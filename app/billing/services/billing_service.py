from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.audit.services.audit_service import AuditService
from app.core.services.base_atomic_service import BaseAtomicService
from app.users.models import User


class BillingService(BaseAtomicService):
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

        order.status = OrderStatus.BILLED

        db.commit()
        db.refresh(order)

        AuditService.log(
            db=db,
            action="order:bill",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=f"Order {order.id} billed by {current_user.username}",
        )

        return order
