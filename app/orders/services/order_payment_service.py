from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.users.models.user import User


class OrderPaymentService:
    @staticmethod
    def mark_paid(
        db: Session,
        *,
        order: Order,
        current_user: User,
    ) -> Order:
        if order.status == OrderStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pedido cancelado não pode ser marcado como pago.",
            )
        if order.is_paid:
            return order

        with atomic(db):
            order.is_paid = True

            AuditService.log(
                db=db,
                action="order:mark_paid",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=f"Order {order.id} marked as paid by {current_user.username}",
            )

        db.refresh(order)
        return order
