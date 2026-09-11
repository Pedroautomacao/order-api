"""Produtor avisado quando o pedido é cancelado no meio da produção.

O cancelamento limpa o assigned_user_id, então sem guarda específica o produtor
recebia "pedido não atribuído" — mensagem que não diz o que houve.
"""
import pytest

from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.exception_handler import OrderCanceledDuringProductionException
from app.orders.schemas.order_item_schema import OrderItemConfirm
from app.orders.services.order_cancel_service import OrderCancelService
from app.orders.services.order_item_service import OrderItemService
from app.orders.services.order_service import OrderService

from tests.conftest import make_order


@pytest.fixture()
def em_producao(catalog):
    make_order(catalog)
    return OrderService.assign_next_order(catalog.db, current_user=catalog.user)


def _cancelar(catalog, order):
    return OrderCancelService.cancel(
        db=catalog.db, order=order, current_user=catalog.user, is_admin=True
    )


def _item_em_producao(order):
    return next(i for i in order.items if i.status == OrderItemStatus.PRODUCING)


class TestAvisoAoProdutor:
    def test_confirmar_item_avisa_do_cancelamento(self, catalog, em_producao):
        item = _item_em_producao(em_producao)
        _cancelar(catalog, em_producao)

        with pytest.raises(OrderCanceledDuringProductionException) as erro:
            OrderItemService.confirm_item(
                catalog.db,
                order_item_id=item.id,
                data=OrderItemConfirm(producedQuantity=1),
                current_user=catalog.user,
            )

        assert f"#{em_producao.id}" in erro.value.message
        assert "cancelado" in erro.value.message.lower()

    def test_a_resposta_e_409(self, catalog, em_producao):
        item = _item_em_producao(em_producao)
        _cancelar(catalog, em_producao)

        with pytest.raises(OrderCanceledDuringProductionException) as erro:
            OrderItemService.confirm_item(
                catalog.db,
                order_item_id=item.id,
                data=OrderItemConfirm(producedQuantity=1),
                current_user=catalog.user,
            )

        assert erro.value.status_code == 409


class TestEstadoDepoisDoCancelamento:
    def test_o_pedido_fica_cancelado_e_sem_produtor(self, catalog, em_producao):
        _cancelar(catalog, em_producao)
        catalog.db.refresh(em_producao)

        assert em_producao.status == OrderStatus.CANCELED
        assert em_producao.assigned_user_id is None

    def test_o_produtor_nao_pega_o_pedido_cancelado_de_volta(self, catalog, em_producao):
        _cancelar(catalog, em_producao)

        from app.orders.exception_handler import NoOrderAvailableException

        with pytest.raises(NoOrderAvailableException):
            OrderService.assign_next_order(catalog.db, current_user=catalog.user)
