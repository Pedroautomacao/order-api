from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.users.models import User


class BillingService:
    @staticmethod
    def bill(
        db: Session,
        *,
        order: Order,
        current_user: User,
    ) -> Order:
        if order.status != OrderStatus.PRODUCED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only produced orders can be billed",
            )

        with atomic(db):
            order.status = OrderStatus.BILLED

            AuditService.log(
                db=db,
                action="order:bill",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=f"Pedido #{order.id} faturado",
            )

        db.refresh(order)
        return order
