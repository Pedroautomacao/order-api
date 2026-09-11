"""Unidade de trabalho: dado e log de auditoria numa transação só."""
from datetime import date, timedelta, timezone

import pytest

from app.audit.models.audit_log import AuditLog
from app.core.time import utcnow
from app.orders.models.order import Order
from app.orders.enums import PaymentMethod
from app.orders.schemas.order_item_schema import OrderItemCreate
from app.orders.schemas.order_schema import OrderCreate
from app.orders.services.order_service import OrderService
from app.products.exception_handler import ProductNotFoundException
from app.core.time import min_scheduled_date


def data_permitida():
    """Primeira data que a criação aceita — hoje só até as 16h de São Paulo."""
    return min_scheduled_date()


def payload(catalog, product_id):
    return OrderCreate(
        client_id=catalog.client.id,
        scheduled_date=data_permitida(),
        payment_method=PaymentMethod.CASH,
        items=[OrderItemCreate(product_id=product_id, quantity=2)],
    )


class TestCriacao:
    def test_grava_pedido_e_log_juntos(self, catalog):
        OrderService.create(
            catalog.db, data=payload(catalog, catalog.alfa.id), current_user=catalog.user
        )

        logs = catalog.db.query(AuditLog).filter_by(action="order:create").all()
        assert len(logs) == 1

    def test_log_aponta_para_o_pedido_criado(self, catalog):
        order = OrderService.create(
            catalog.db, data=payload(catalog, catalog.alfa.id), current_user=catalog.user
        )

        log = catalog.db.query(AuditLog).filter_by(action="order:create").one()
        assert log.entity_id == order.id


class TestRollback:
    def test_falha_no_meio_nao_deixa_pedido(self, catalog):
        antes = catalog.db.query(Order).count()

        with pytest.raises(ProductNotFoundException):
            OrderService.create(
                catalog.db, data=payload(catalog, 999999), current_user=catalog.user
            )
        catalog.db.rollback()

        assert catalog.db.query(Order).count() == antes

    def test_falha_no_meio_nao_deixa_log_orfao(self, catalog):
        antes = catalog.db.query(AuditLog).count()

        with pytest.raises(ProductNotFoundException):
            OrderService.create(
                catalog.db, data=payload(catalog, 999999), current_user=catalog.user
            )
        catalog.db.rollback()

        assert catalog.db.query(AuditLog).count() == antes


class TestAuditService:
    def test_log_nao_commita_sozinho(self, catalog):
        """O log participa da transação de quem chama, e não de uma própria."""
        from app.audit.services.audit_service import AuditService

        AuditService.log(
            db=catalog.db,
            action="teste",
            entity="teste",
            entity_id=1,
            user_id=catalog.user.id,
            description="sem commit",
        )
        catalog.db.rollback()

        assert catalog.db.query(AuditLog).filter_by(action="teste").count() == 0
