"""Ciclo de produção: atribuir, confirmar itens, finalizar e resetar."""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.order_item_breaks.models import OrderItemBreak
from app.orders.enums import OrderItemStatus, OrderStatus, PaymentMethod
from app.orders.models.work_item import WorkItem
from app.orders.models.work_order import WorkOrder
from app.orders.services.order_finish_service import OrderFinishService
from app.orders.services.order_reset_service import OrderResetService
from app.orders.services.order_service import OrderService
from app.orders.services.order_update_service import OrderUpdateService

from tests.conftest import confirm_next_item, make_order
from app.core.time import today_sp


def abertos(db, model, order_id):
    return (
        db.query(model)
        .filter(
            model.order_id == order_id,
            model.ended_at.is_(None),
            model.is_deleted.is_(False),
        )
        .all()
    )


class TestCicloCompleto:
    def test_atribuir_abre_uma_work_order(self, catalog):
        make_order(catalog)

        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        assert order.status == OrderStatus.PRODUCING
        assert len(abertos(catalog.db, WorkOrder, order.id)) == 1

    def test_finalizar_fecha_a_work_order_com_tempo(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order)
        confirm_next_item(catalog, order)

        OrderFinishService.finish_order(
            db=catalog.db, order=order, current_user=catalog.user
        )

        work_order = (
            catalog.db.query(WorkOrder)
            .filter(WorkOrder.order_id == order.id, WorkOrder.is_deleted.is_(False))
            .one()
        )
        assert work_order.ended_at is not None
        assert work_order.time_to_produced_secs is not None

    def test_confirmar_itens_nao_deixa_work_item_aberto(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        confirm_next_item(catalog, order)
        confirm_next_item(catalog, order)

        assert abertos(catalog.db, WorkItem, order.id) == []


class TestFinalizar:
    def test_sem_work_order_nao_quebra(self, catalog):
        """Pedidos que entraram em produção antes da WorkOrder existir."""
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order)
        confirm_next_item(catalog, order)
        catalog.db.query(WorkOrder).filter(WorkOrder.order_id == order.id).delete()
        catalog.db.commit()

        finalizado = OrderFinishService.finish_order(
            db=catalog.db, order=order, current_user=catalog.user
        )

        assert finalizado.status == OrderStatus.PRODUCED

    @pytest.mark.parametrize(
        "status", [OrderStatus.AWAITING, OrderStatus.PRODUCED, OrderStatus.BILLED]
    )
    def test_exige_pedido_em_producao(self, catalog, status):
        order = make_order(catalog, status=status, item_status=OrderItemStatus.PRODUCED)

        with pytest.raises(HTTPException) as erro:
            OrderFinishService.finish_order(
                db=catalog.db, order=order, current_user=catalog.user
            )

        assert erro.value.status_code == 400


class TestReset:
    @pytest.fixture()
    def resetado(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order, produced_quantity=1)  # gera uma quebra
        anterior = (
            catalog.db.query(WorkOrder).filter(WorkOrder.order_id == order.id).one()
        )
        OrderResetService.reset(db=catalog.db, order=order, current_user=catalog.user)
        return SimpleNamespace(order=order, work_order_anterior=anterior)

    def test_volta_para_aguardando(self, catalog, resetado):
        assert resetado.order.status == OrderStatus.AWAITING
        assert resetado.order.assigned_user_id is None

    def test_nao_deixa_apontamento_aberto_do_ciclo_anterior(self, catalog, resetado):
        assert abertos(catalog.db, WorkOrder, resetado.order.id) == []
        assert abertos(catalog.db, WorkItem, resetado.order.id) == []

    def test_zera_os_tempos_para_ficarem_fora_das_medias(self, catalog, resetado):
        anterior = catalog.db.get(WorkOrder, resetado.work_order_anterior.id)

        assert anterior.time_to_produced_secs is None

    def test_invalida_as_quebras_do_ciclo_anulado(self, catalog, resetado):
        vivas = (
            catalog.db.query(OrderItemBreak)
            .filter(
                OrderItemBreak.order_id == resetado.order.id,
                OrderItemBreak.is_deleted.is_(False),
            )
            .count()
        )

        assert vivas == 0

    def test_novo_ciclo_abre_apontamento_proprio(self, catalog, resetado):
        novo = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        abertas = abertos(catalog.db, WorkOrder, novo.id)

        assert len(abertas) == 1
        assert abertas[0].id != resetado.work_order_anterior.id

    def test_finalizar_o_novo_ciclo_fecha_o_apontamento_certo(self, catalog, resetado):
        novo = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, novo)
        confirm_next_item(catalog, novo)

        OrderFinishService.finish_order(
            db=catalog.db, order=novo, current_user=catalog.user
        )

        atual = (
            catalog.db.query(WorkOrder)
            .filter(WorkOrder.order_id == novo.id, WorkOrder.is_deleted.is_(False))
            .one()
        )
        anterior = catalog.db.get(WorkOrder, resetado.work_order_anterior.id)
        assert atual.ended_at is not None
        assert anterior.ended_at is None, "o ciclo anulado não pode ser fechado"


class TestEdicaoDoVendedor:
    def test_recusa_lista_de_itens_vazia(self, catalog):
        """Sem esta guarda o PUT apagava todos os itens e zerava o total."""
        order = make_order(catalog)
        antes = len(order.items)
        payload = SimpleNamespace(
            client_id=catalog.client.id,
            scheduled_date=today_sp(),
            payment_method=PaymentMethod.CASH,
            items=[],
        )

        with pytest.raises(ValueError, match="at least one item"):
            OrderUpdateService.update(
                catalog.db, order=order, data=payload, current_user=catalog.user
            )

        catalog.db.rollback()
        assert len(order.items) == antes


class TestEdicaoDeQuantidadeDepoisDaProducao:
    """O finish não limpa assigned_user_id: sem guarda de status o produtor
    continuava alterando a quantidade de um pedido já finalizado ou faturado."""

    @pytest.fixture()
    def finalizado(self, catalog):
        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order)
        OrderFinishService.finish_order(
            db=catalog.db, order=order, current_user=catalog.user
        )
        return order

    def test_bloqueia_em_pedido_finalizado(self, catalog, finalizado):
        from app.orders.exception_handler import OrderNotInProductionException
        from app.orders.services.order_item_service import OrderItemService

        item = finalizado.items[0]
        antes = item.produced_quantity

        with pytest.raises(OrderNotInProductionException):
            OrderItemService.update_produced_quantity(
                catalog.db,
                order_item_id=item.id,
                data=SimpleNamespace(produced_quantity=1),
                current_user=catalog.user,
            )

        catalog.db.rollback()
        assert catalog.db.get(type(item), item.id).produced_quantity == antes

    def test_bloqueia_em_pedido_faturado(self, catalog, finalizado):
        from app.billing.services.billing_service import BillingService
        from app.orders.exception_handler import OrderNotInProductionException
        from app.orders.services.order_item_service import OrderItemService

        BillingService.bill(db=catalog.db, order=finalizado, current_user=catalog.user)

        with pytest.raises(OrderNotInProductionException):
            OrderItemService.update_produced_quantity(
                catalog.db,
                order_item_id=finalizado.items[0].id,
                data=SimpleNamespace(produced_quantity=99),
                current_user=catalog.user,
            )

    def test_permite_durante_a_producao(self, catalog):
        from app.orders.services.order_item_service import OrderItemService

        make_order(catalog, products=[catalog.alfa, catalog.zulu])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order)
        produzido = next(
            i for i in order.items if i.status == OrderItemStatus.PRODUCED
        )

        OrderItemService.update_produced_quantity(
            catalog.db,
            order_item_id=produzido.id,
            data=SimpleNamespace(produced_quantity=3),
            current_user=catalog.user,
        )

        catalog.db.refresh(produzido)
        assert produzido.produced_quantity == 3


class TestCancelamento:
    """Cancelar deixava o item em Producing e os apontamentos abertos para sempre."""

    @pytest.fixture()
    def cancelado(self, catalog):
        from app.orders.services.order_cancel_service import OrderCancelService

        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order, produced_quantity=1)  # gera quebra
        OrderCancelService.cancel(
            db=catalog.db, order=order, current_user=catalog.user, is_admin=True
        )
        return order

    def test_nao_deixa_apontamento_aberto(self, catalog, cancelado):
        assert abertos(catalog.db, WorkOrder, cancelado.id) == []
        assert abertos(catalog.db, WorkItem, cancelado.id) == []

    def test_baixa_o_item_que_estava_em_producao(self, catalog, cancelado):
        catalog.db.expire_all()
        producing = [
            i for i in cancelado.items if i.status == OrderItemStatus.PRODUCING
        ]

        assert producing == []

    def test_anula_as_quebras_do_ciclo_cancelado(self, catalog, cancelado):
        vivas = (
            catalog.db.query(OrderItemBreak)
            .filter(
                OrderItemBreak.order_id == cancelado.id,
                OrderItemBreak.is_deleted.is_(False),
            )
            .count()
        )

        assert vivas == 0


class TestPedidoSemItens:
    def test_finish_recusa(self, catalog):
        """any() sobre lista vazia é False: o pedido era finalizado sem produzir nada."""
        from app.orders.exception_handler import OrderNotFinishedException

        order = make_order(catalog, status=OrderStatus.PRODUCING, products=[])

        with pytest.raises(OrderNotFinishedException):
            OrderFinishService.finish_order(
                db=catalog.db, order=order, current_user=catalog.user
            )


class TestConfirmSemApontamento:
    def test_nao_trava_o_pedido(self, catalog):
        """Item sem WorkItem aberto estourava e o pedido não confirmava nem finalizava."""
        from app.orders.services.order_item_service import OrderItemService

        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        catalog.db.query(WorkItem).filter(WorkItem.order_id == order.id).delete()
        catalog.db.commit()
        item = order.items[0]

        OrderItemService.confirm_item(
            catalog.db,
            order_item_id=item.id,
            data=SimpleNamespace(produced_quantity=item.quantity),
            current_user=catalog.user,
        )

        catalog.db.refresh(item)
        assert item.status == OrderItemStatus.PRODUCED


class TestCorrecaoDeQuantidade:
    """O update apagava fisicamente TODAS as quebras do item, inclusive as que o
    reset havia preservado como histórico de um ciclo anulado."""

    @pytest.fixture()
    def com_quebra(self, catalog):
        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order, produced_quantity=1)  # previsto 5
        return order

    def test_quebra_vigente_reflete_a_correcao(self, catalog, com_quebra):
        from app.orders.services.order_item_service import OrderItemService

        item = com_quebra.items[0]

        OrderItemService.update_produced_quantity(
            catalog.db,
            order_item_id=item.id,
            data=SimpleNamespace(produced_quantity=4),
            current_user=catalog.user,
        )

        vigentes = (
            catalog.db.query(OrderItemBreak)
            .filter(
                OrderItemBreak.order_item_id == item.id,
                OrderItemBreak.is_deleted.is_(False),
            )
            .all()
        )
        assert len(vigentes) == 1
        assert float(vigentes[0].confirmed_quantity) == 4

    def test_quebra_anterior_vira_historico_em_vez_de_sumir(self, catalog, com_quebra):
        from app.orders.services.order_item_service import OrderItemService

        item = com_quebra.items[0]

        OrderItemService.update_produced_quantity(
            catalog.db,
            order_item_id=item.id,
            data=SimpleNamespace(produced_quantity=4),
            current_user=catalog.user,
        )

        anuladas = (
            catalog.db.query(OrderItemBreak)
            .filter(
                OrderItemBreak.order_item_id == item.id,
                OrderItemBreak.is_deleted.is_(True),
            )
            .all()
        )
        assert len(anuladas) == 1
        assert float(anuladas[0].confirmed_quantity) == 1

    def test_correcao_sem_quebra_nao_deixa_quebra_vigente(self, catalog, com_quebra):
        """Corrigir para a quantidade prevista tem de zerar a quebra."""
        from app.orders.services.order_item_service import OrderItemService

        item = com_quebra.items[0]

        OrderItemService.update_produced_quantity(
            catalog.db,
            order_item_id=item.id,
            data=SimpleNamespace(produced_quantity=item.quantity),
            current_user=catalog.user,
        )

        vigentes = (
            catalog.db.query(OrderItemBreak)
            .filter(
                OrderItemBreak.order_item_id == item.id,
                OrderItemBreak.is_deleted.is_(False),
            )
            .count()
        )
        assert vigentes == 0
