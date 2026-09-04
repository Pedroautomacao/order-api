"""Contrato de OrderResponse: o que a tela de detalhe consome.

Regressão do bug em que um pedido em Aguardando respondia `produced_items: []`
e `current_item: null` — a tela renderizava "Nenhum item" mesmo com itens.
"""
import pytest

from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.serializers.order_serializer import serialize_order
from app.orders.services.order_finish_service import OrderFinishService
from app.orders.services.order_service import OrderService
from app.orders.utils.split_order_item import split_order_items

from tests.conftest import confirm_next_item, make_order


class TestListaDeItens:
    def test_pedido_aguardando_expoe_seus_itens(self, catalog):
        order = make_order(catalog)

        resposta = serialize_order(order)

        assert len(resposta.items) == 2
        assert resposta.total_items == 2

    def test_produced_items_e_current_item_seguem_sendo_o_recorte_do_produtor(
        self, catalog
    ):
        """A tela do produtor depende desses dois campos e não pode mudar."""
        order = make_order(catalog)

        resposta = serialize_order(order)

        assert resposta.produced_items == []
        assert resposta.current_item is None

    def test_pedido_em_producao_mostra_o_item_que_ainda_nao_comecou(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        resposta = serialize_order(order)

        assert len(resposta.items) == 2, "o item em Aguardando também precisa aparecer"
        assert resposta.current_item is not None
        assert resposta.produced_items == []

    def test_items_vem_ordenado_por_nome_do_produto(self, catalog):
        """Order.items não tem ORDER BY: sem ordenar, a tabela troca de ordem."""
        order = make_order(catalog, products=[catalog.zulu, catalog.alfa])

        resposta = serialize_order(order)

        assert [i.product.name for i in resposta.items] == ["Alfa", "Zulu"]


class TestIdsDoFormularioDeEdicao:
    """O modal de edição do vendedor monta o payload a partir desses ids."""

    def test_response_expoe_client_id(self, catalog):
        order = make_order(catalog)

        assert serialize_order(order).client_id == catalog.client.id

    def test_item_expoe_product_id_e_order_id(self, catalog):
        order = make_order(catalog)

        item = serialize_order(order).items[0]

        assert item.product_id is not None
        assert item.order_id == order.id


class TestCanFinish:
    """Espelha a regra do servidor: em produção, com itens, e todos produzidos."""

    @pytest.mark.parametrize(
        "status",
        [OrderStatus.AWAITING, OrderStatus.PRODUCED, OrderStatus.BILLED, OrderStatus.CANCELED],
    )
    def test_falso_fora_de_producao(self, catalog, status):
        order = make_order(catalog, status=status, item_status=OrderItemStatus.PRODUCED)

        assert serialize_order(order).can_finish is False

    def test_falso_com_item_pendente(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        confirm_next_item(catalog, order)

        assert serialize_order(order).can_finish is False

    def test_verdadeiro_com_tudo_produzido(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)

        confirm_next_item(catalog, order)
        confirm_next_item(catalog, order)

        assert serialize_order(order).can_finish is True

    def test_volta_a_falso_depois_de_finalizado(self, catalog):
        make_order(catalog)
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order)
        confirm_next_item(catalog, order)

        finalizado = OrderFinishService.finish_order(
            db=catalog.db, order=order, current_user=catalog.user
        )

        assert serialize_order(finalizado).can_finish is False


class TestSplitOrderItems:
    def test_com_dois_itens_em_producao_escolhe_sempre_o_mesmo(self, catalog):
        """Estado inconsistente não deve mudar de resposta entre requisições."""
        order = make_order(catalog, item_status=OrderItemStatus.PRODUCING)

        primeiro = split_order_items(order)[1]
        segundo = split_order_items(order)[1]

        assert primeiro is not None
        assert primeiro.id == segundo.id
        assert primeiro.id == min(i.id for i in order.items)


class TestAutoria:
    """A tela de detalhe mostra quem registrou o pedido, não o id."""

    def test_response_expoe_o_criador_com_nome(self, catalog):
        order = make_order(catalog)

        criador = serialize_order(order).created_by

        assert criador is not None
        assert criador.id == catalog.user.id
        assert criador.username == "produtor"
        assert criador.full_name == "Produtor Teste"

    def test_created_by_user_id_continua_no_contrato(self, catalog):
        """Campo antigo mantido: o front pode estar em versão anterior."""
        order = make_order(catalog)

        assert serialize_order(order).created_by_user_id == catalog.user.id

    def test_full_name_cai_no_username_sem_nome(self, catalog):
        from app.users.models.user import User

        anonimo = User(
            username="semnome",
            first_name="",
            last_name="",
            cpf="999",
            password_hash="x",
            is_active=True,
        )

        assert anonimo.full_name == "semnome"
