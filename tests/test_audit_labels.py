"""Auditoria em português: rótulos de ação/entidade e descrições geradas.

As descrições são f-strings montadas dentro de cada serviço — só um teste que
executa o fluxo prova que elas não estouram em runtime (atributo inexistente,
data nula, produto sem unidade).
"""
import re
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.audit.labels import ACTION_LABELS, ENTITY_LABELS, action_label, entity_label
from app.audit.models.audit_log import AuditLog
from app.audit.schemas.audit_schema import AuditLogResponse
from app.orders.enums import OrderItemStatus, OrderStatus, PaymentMethod
from app.orders.services.order_finish_service import OrderFinishService
from app.orders.services.order_service import OrderService

from tests.conftest import confirm_next_item, make_order

INGLES = re.compile(
    r"\b(created|updated|deleted|canceled|billed|finished|assigned|reset|"
    r"produced|password|order|client|product|unit|user|by)\b",
    re.IGNORECASE,
)


def logs_de(db, action):
    return db.query(AuditLog).filter(AuditLog.action == action).all()


class TestRotulos:
    def test_toda_acao_gravada_tem_rotulo(self):
        """Se alguém criar uma ação nova sem rótulo, este teste avisa."""
        import pathlib

        usadas = set()
        for arquivo in pathlib.Path("app").rglob("*.py"):
            usadas |= set(
                re.findall(r'action="([^"]+)"', arquivo.read_text(encoding="utf-8"))
            )

        assert usadas - set(ACTION_LABELS) == set()

    def test_toda_entidade_gravada_tem_rotulo(self):
        import pathlib

        usadas = set()
        for arquivo in pathlib.Path("app").rglob("*.py"):
            usadas |= set(
                re.findall(r'entity="([^"]+)"', arquivo.read_text(encoding="utf-8"))
            )

        assert usadas - set(ENTITY_LABELS) == set()

    def test_chave_desconhecida_nao_quebra_a_tela(self):
        """Log antigo com ação que não existe mais cai no próprio valor."""
        assert action_label("algo:inexistente") == "algo:inexistente"
        assert entity_label(None) == "-"

    def test_resposta_expoe_chave_e_rotulo(self):
        log = AuditLog(
            id=1,
            action="order:bill",
            entity="order",
            entity_id=7,
            description="Pedido #7 faturado",
            user_id=1,
            created_at=date.today(),
        )

        corpo = AuditLogResponse.model_validate(log).model_dump()

        assert corpo["action"] == "order:bill", "a chave crua é o que o filtro usa"
        assert corpo["action_label"] == "Pedido faturado"
        assert corpo["entity_label"] == "Pedido"


class TestDescricoesGeradas:
    def test_criar_pedido(self, catalog):
        from app.orders.schemas.order_item_schema import OrderItemCreate
        from app.orders.schemas.order_schema import OrderCreate
        from app.core.time import utcnow
        from datetime import timezone

        agora_br = utcnow().astimezone(timezone(timedelta(hours=-3)))
        agendada = date.today() + timedelta(days=1) if agora_br.hour >= 16 else date.today()

        OrderService.create(
            catalog.db,
            data=OrderCreate(
                client_id=catalog.client.id,
                scheduled_date=agendada,
                payment_method=PaymentMethod.CASH,
                items=[OrderItemCreate(product_id=catalog.alfa.id, quantity=2)],
            ),
            current_user=catalog.user,
        )

        descricao = logs_de(catalog.db, "order:create")[0].description
        assert catalog.client.name in descricao
        assert agendada.strftime("%d/%m/%Y") in descricao

    def test_atribuir_confirmar_e_finalizar(self, catalog):
        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order, produced_quantity=3)
        OrderFinishService.finish_order(
            db=catalog.db, order=order, current_user=catalog.user
        )

        assert f"#{order.id}" in logs_de(catalog.db, "order:assign")[0].description
        confirmacao = logs_de(catalog.db, "order:item_confirm")[0].description
        assert "Alfa" in confirmacao and "(kg)" in confirmacao
        assert "3" in confirmacao
        assert "finalizada" in logs_de(catalog.db, "order:finish")[0].description

    def test_corrigir_quantidade(self, catalog):
        from app.orders.services.order_item_service import OrderItemService

        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order, produced_quantity=3)

        OrderItemService.update_produced_quantity(
            catalog.db,
            order_item_id=order.items[0].id,
            data=SimpleNamespace(produced_quantity=4),
            current_user=catalog.user,
        )

        descricao = logs_de(catalog.db, "order:item_update_quantity")[0].description
        assert "corrigida de" in descricao
        assert "3" in descricao and "4" in descricao

    def test_remarcar_data(self, catalog):
        from app.orders.services.order_admin_service import OrderAdminService

        order = make_order(catalog, products=[catalog.alfa])
        nova = date.today() + timedelta(days=3)

        OrderAdminService.reschedule(
            catalog.db, order=order, new_date=nova, current_user=catalog.user
        )

        descricao = logs_de(catalog.db, "order:reschedule")[0].description
        assert nova.strftime("%d/%m/%Y") in descricao

    def test_cancelar_e_reiniciar(self, catalog):
        from app.orders.services.order_cancel_service import OrderCancelService
        from app.orders.services.order_reset_service import OrderResetService

        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        OrderResetService.reset(
            db=catalog.db, order=order, current_user=catalog.user
        )
        OrderCancelService.cancel(
            db=catalog.db, order=order, current_user=catalog.user, is_admin=True
        )

        assert "reiniciada" in logs_de(catalog.db, "order:reset_production")[0].description
        assert "cancelado" in logs_de(catalog.db, "order:cancel")[0].description

    def test_faturar(self, catalog):
        from app.billing.services.billing_service import BillingService

        order = make_order(
            catalog,
            status=OrderStatus.PRODUCED,
            products=[catalog.alfa],
            item_status=OrderItemStatus.PRODUCED,
        )

        BillingService.bill(db=catalog.db, order=order, current_user=catalog.user)

        assert logs_de(catalog.db, "order:bill")[0].description == (
            f"Pedido #{order.id} faturado"
        )

    @pytest.mark.parametrize(
        "acao",
        [
            "order:create",
            "order:assign",
            "order:item_confirm",
            "order:finish",
            "order:bill",
        ],
    )
    def test_nenhuma_descricao_do_fluxo_sobrou_em_ingles(self, catalog, acao):
        from app.billing.services.billing_service import BillingService

        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        confirm_next_item(catalog, order)
        OrderFinishService.finish_order(
            db=catalog.db, order=order, current_user=catalog.user
        )
        BillingService.bill(db=catalog.db, order=order, current_user=catalog.user)

        for log in logs_de(catalog.db, acao):
            assert not INGLES.search(log.description or ""), log.description


class TestDescricoesDeCadastro:
    def test_cliente_produto_unidade_e_usuario(self, catalog):
        from app.clients.schemas.client_schema import ClientCreate
        from app.clients.services.client_service import ClientService
        from app.products.schemas.product_schema import ProductCreate
        from app.products.services.product_service import ProductService
        from app.units.schemas.unit_schema import UnitCreate
        from app.units.services.unit_service import UnitService

        ClientService.create(
            catalog.db,
            data=ClientCreate(
                name="Mercado Novo",
                priority="B",
                cpf_cnpj="111",
                address="Rua 2",
                phone_number="8",
                observations="",
                is_active=True,
                allow_cash=True,
                allow_credit=False,
                credit_limit=0,
            ),
            current_user=catalog.user,
        )
        unidade = UnitService.create(
            catalog.db,
            data=UnitCreate(code="lt", name="Litro", description="d", is_active=True),
            current_user=catalog.user,
        )
        ProductService.create(
            catalog.db,
            data=ProductCreate(
                name="Gama",
                description="d",
                sku="G",
                is_active=True,
                unit_price=5,
                unit_of_measure_id=unidade.id,
            ),
            current_user=catalog.user,
        )

        assert logs_de(catalog.db, "client:create")[0].description == (
            "Cliente Mercado Novo cadastrado"
        )
        assert logs_de(catalog.db, "unit:create")[0].description == (
            "Unidade Litro (lt) cadastrada"
        )
        assert logs_de(catalog.db, "product:create")[0].description == (
            "Produto Gama cadastrado"
        )

    def test_troca_de_senha(self, catalog):
        from app.users.services.user_service import UserService

        UserService.reset_password(
            catalog.db,
            user=catalog.user,
            new_password="Nova@1234",
            admin_user=catalog.user,
        )

        descricao = logs_de(catalog.db, "user:reset_password")[0].description
        assert catalog.user.username in descricao
        assert "sessões ativas encerradas" in descricao
