from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.audit.services.audit_service import AuditService


class OrderCancelService:
    @staticmethod
    def cancel(
        *,
        db: Session,
        order: Order,
        current_user,
        is_admin: bool,
    ) -> Order:
        if order.status == OrderStatus.BILLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pedidos faturados não podem ser cancelados.",
            )

        if order.status == OrderStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pedido já está cancelado.",
            )

        if not is_admin and order.status == OrderStatus.PRODUCING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order in production cannot be canceled by creator.",
            )

        order.status = OrderStatus.CANCELED
        order.assigned_user_id = None

        db.commit()
        db.refresh(order)

        AuditService.log(
            db=db,
            action="order:cancel",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=f"Order {order.id} canceled by {current_user.username}",
        )

        return order
