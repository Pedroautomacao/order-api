"""Preço do item congelado no pedido, e edição de quantidade e preço.

order_items não guardava preço: a tela mostrava products.unit_price, o preço
atual. Quando o produto mudava de preço, o pedido antigo passava a exibir um
valor que nunca foi cobrado.
"""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.time import min_scheduled_date
from app.orders.enums import OrderStatus
from app.orders.schemas.order_item_schema import OrderItemCreate
from app.orders.schemas.order_schema import OrderCreate, OrderUpdate
from app.orders.services.order_service import OrderService
from app.orders.services.order_update_service import OrderUpdateService

from tests.conftest import make_order


def _criar(catalog, itens):
    return OrderService.create(
        catalog.db,
        data=OrderCreate(
            client_id=catalog.client.id,
            scheduled_date=min_scheduled_date(),
            items=itens,
        ),
        current_user=catalog.user,
    )


def _item(produto, quantidade, preco=None):
    dados = {"product_id": produto.id, "quantity": quantidade}
    if preco is not None:
        dados["unit_price"] = preco
    return OrderItemCreate(**dados)


class TestPrecoCongelado:
    def test_usa_o_preco_de_tabela_do_produto(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 3)])

        assert pedido.items[0].unit_price == Decimal("10")

    def test_mudar_o_preco_do_produto_nao_altera_o_pedido(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 3)])

        catalog.alfa.unit_price = Decimal("99")
        catalog.db.commit()
        catalog.db.refresh(pedido)

        assert pedido.items[0].unit_price == Decimal("10")
        assert pedido.total_amount == Decimal("30")

    def test_total_da_linha_e_preco_vezes_quantidade(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 3)])

        assert pedido.items[0].total_price == Decimal("30")


class TestDescontoExclusivo:
    def test_preco_informado_vence_o_de_tabela(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 2, Decimal("7.50"))])

        assert pedido.items[0].unit_price == Decimal("7.50")

    def test_o_total_do_pedido_sai_do_preco_informado(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 2, Decimal("7.50"))])

        assert pedido.total_amount == Decimal("15.00")

    def test_o_preco_de_tabela_do_produto_nao_muda(self, catalog):
        _criar(catalog, [_item(catalog.alfa, 2, Decimal("7.50"))])
        catalog.db.refresh(catalog.alfa)

        assert catalog.alfa.unit_price == Decimal("10")


class TestEdicao:
    def _editar(self, catalog, pedido, itens, **kwargs):
        return OrderUpdateService.update(
            catalog.db,
            order=pedido,
            data=OrderUpdate(
                client_id=catalog.client.id,
                scheduled_date=min_scheduled_date(),
                items=itens,
            ),
            current_user=catalog.user,
            **kwargs,
        )

    def test_alterar_a_quantidade_recalcula_o_total(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 2)])

        self._editar(catalog, pedido, [_item(catalog.alfa, 5)])

        assert pedido.total_amount == Decimal("50")

    def test_alterar_o_preco_recalcula_o_total(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 2)])

        self._editar(catalog, pedido, [_item(catalog.alfa, 2, Decimal("4"))])

        assert pedido.items[0].unit_price == Decimal("4")
        assert pedido.total_amount == Decimal("8")

    def test_alterar_preco_e_quantidade_juntos(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 2)])

        self._editar(catalog, pedido, [_item(catalog.alfa, 3, Decimal("6"))])

        assert pedido.total_amount == Decimal("18")

    def test_so_edita_pedido_em_aguardando(self, catalog):
        pedido = make_order(catalog, status=OrderStatus.PRODUCING)

        with pytest.raises(HTTPException) as exc:
            self._editar(catalog, pedido, [_item(catalog.alfa, 1)])

        assert exc.value.status_code == 400


class TestQuemPodeEditar:
    def _dados(self, catalog):
        return OrderUpdate(
            client_id=catalog.client.id,
            scheduled_date=min_scheduled_date(),
            items=[OrderItemCreate(product_id=catalog.alfa.id, quantity=1)],
        )

    def test_o_vendedor_nao_edita_pedido_de_outro(self, catalog):
        pedido = _criar(catalog, [_item(catalog.alfa, 1)])
        pedido.created_by_user_id = catalog.user.id + 999
        catalog.db.flush()

        with pytest.raises(HTTPException) as exc:
            OrderUpdateService.update(
                catalog.db,
                order=pedido,
                data=self._dados(catalog),
                current_user=catalog.user,
            )

        assert exc.value.status_code == 403

    def test_a_edicao_administrativa_dispensa_a_posse(self, catalog):
        """A rota já exigiu order:update, então o dono não importa."""
        pedido = _criar(catalog, [_item(catalog.alfa, 1)])
        pedido.created_by_user_id = catalog.user.id + 999
        catalog.db.flush()

        editado = OrderUpdateService.update(
            catalog.db,
            order=pedido,
            data=self._dados(catalog),
            current_user=catalog.user,
            enforce_ownership=False,
        )

        assert editado.id == pedido.id
