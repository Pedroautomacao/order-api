"""Liberação de produção: só pedido aprovado entra na fila do produtor."""
import pytest
from fastapi import HTTPException

from app.orders.enums import OrderStatus, ProductionApproval
from app.orders.exception_handler import NoOrderAvailableException
from app.orders.routes.order_routes import list_orders
from app.orders.services.order_production_approval_service import (
    OrderProductionApprovalService,
)
from app.orders.services.order_service import OrderService

from tests.conftest import make_order


def aprovar(catalog, order):
    return OrderProductionApprovalService.approve(
        catalog.db, order=order, current_user=catalog.user
    )


def recusar(catalog, order):
    return OrderProductionApprovalService.recuse(
        catalog.db, order=order, current_user=catalog.user
    )


def listar(catalog, **kwargs):
    params = {
        "search": None,
        "status": None,
        "production_approval": None,
        "scheduled_date": None,
        "page": 1,
        "page_size": 20,
    }
    params.update(kwargs)
    return list_orders(db=catalog.db, current_user=catalog.user, **params)


class TestValorInicial:
    def test_pedido_nasce_aguardando_aprovacao(self, catalog):
        # com o atributo em None o SQLAlchemy aplica o default da coluna,
        # que é o mesmo caminho de um pedido criado pela aplicação
        order = make_order(catalog, production_approval=None)
        catalog.db.refresh(order)

        assert order.production_approval == ProductionApproval.AWAITING


class TestFilaDoProdutor:
    def test_pedido_aguardando_aprovacao_nao_entra_na_fila(self, catalog):
        make_order(catalog, production_approval=ProductionApproval.AWAITING)

        with pytest.raises(NoOrderAvailableException):
            OrderService.assign_next_order(catalog.db, current_user=catalog.user)

    def test_pedido_recusado_nao_entra_na_fila(self, catalog):
        make_order(catalog, production_approval=ProductionApproval.RECUSED)

        with pytest.raises(NoOrderAvailableException):
            OrderService.assign_next_order(catalog.db, current_user=catalog.user)

    def test_pedido_aprovado_entra_na_fila(self, catalog):
        esperado = make_order(catalog, production_approval=ProductionApproval.APPROVED)

        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        assert order.id == esperado.id
        assert order.status == OrderStatus.PRODUCING

    def test_aprovar_destrava_um_pedido_que_estava_barrado(self, catalog):
        barrado = make_order(catalog, production_approval=ProductionApproval.AWAITING)
        with pytest.raises(NoOrderAvailableException):
            OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        aprovar(catalog, barrado)

        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        assert order.id == barrado.id


class TestDecisaoReversivel:
    def test_aprovar_depois_recusar(self, catalog):
        order = make_order(catalog, production_approval=ProductionApproval.AWAITING)

        assert aprovar(catalog, order).production_approval == ProductionApproval.APPROVED
        assert recusar(catalog, order).production_approval == ProductionApproval.RECUSED

    def test_recusar_depois_aprovar(self, catalog):
        order = make_order(catalog, production_approval=ProductionApproval.AWAITING)

        assert recusar(catalog, order).production_approval == ProductionApproval.RECUSED
        assert aprovar(catalog, order).production_approval == ProductionApproval.APPROVED

    def test_aprovar_duas_vezes_e_inofensivo(self, catalog):
        order = make_order(catalog, production_approval=ProductionApproval.APPROVED)

        assert aprovar(catalog, order).production_approval == ProductionApproval.APPROVED


class TestPedidoEncerrado:
    @pytest.mark.parametrize("status", [OrderStatus.CANCELED, OrderStatus.BILLED])
    def test_nao_altera_liberacao_de_pedido_encerrado(self, catalog, status):
        order = make_order(catalog, status=status)

        with pytest.raises(HTTPException) as exc:
            recusar(catalog, order)

        assert exc.value.status_code == 400


class TestFiltroDaListagem:
    def test_filtra_por_liberacao(self, catalog):
        aprovado = make_order(catalog, production_approval=ProductionApproval.APPROVED)
        make_order(catalog, production_approval=ProductionApproval.RECUSED)
        make_order(catalog, production_approval=ProductionApproval.AWAITING)

        page = listar(catalog, production_approval="Approved")

        assert page.total == 1
        assert [o.id for o in page.items] == [aprovado.id]

    def test_valor_invalido_e_ignorado(self, catalog):
        make_order(catalog, production_approval=ProductionApproval.APPROVED)
        make_order(catalog, production_approval=ProductionApproval.RECUSED)

        page = listar(catalog, production_approval="NaoExiste")

        assert page.total == 2
