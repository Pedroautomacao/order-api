from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.models.work_order import WorkOrder
from app.orders.models.work_item import WorkItem
from app.audit.services.audit_service import AuditService


class OrderResetService:
    @staticmethod
    def reset(
        *,
        db: Session,
        order: Order,
        current_user,
    ) -> Order:
        if order.status == OrderStatus.BILLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billed orders cannot be reset.",
            )

        # Reset order
        order.status = OrderStatus.AWAITING
        order.assigned_user_id = None

        # Reset order items
        (
            db.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .update(
                {
                    OrderItem.status: OrderStatus.AWAITING,
                    OrderItem.produced_quantity: 0,
                },
                synchronize_session=False,
            )
        )

        # Reset work orders
        (
            db.query(WorkOrder)
            .filter(WorkOrder.order_id == order.id)
            .update(
                {
                    WorkOrder.ended_at: None,
                    WorkOrder.time_to_produced_secs: None,
                },
                synchronize_session=False,
            )
        )

        # Reset work items
        (
            db.query(WorkItem)
            .filter(WorkItem.order_id == order.id)
            .update(
                {
                    WorkItem.ended_at: None,
                    WorkItem.time_to_produced_secs: None,
                },
                synchronize_session=False,
            )
        )

        db.commit()
        db.refresh(order)

        AuditService.log(
            db=db,
            action="order:reset_production",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=f"Order {order.id} reset by {current_user.username}",
        )

        return order
