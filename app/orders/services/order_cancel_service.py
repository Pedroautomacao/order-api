from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.order_item_breaks.models import OrderItemBreak
from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.models.work_item import WorkItem
from app.orders.models.work_order import WorkOrder


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

        with atomic(db):
            order.status = OrderStatus.CANCELED
            order.assigned_user_id = None

            # Mesmo tratamento do reset: cancelar um pedido em produção
            # deixava o item em Producing e os apontamentos abertos para
            # sempre, sustentando um ciclo que nunca vai terminar.
            (
                db.query(OrderItem)
                .filter(
                    OrderItem.order_id == order.id,
                    OrderItem.status == OrderItemStatus.PRODUCING,
                )
                .update(
                    {OrderItem.status: OrderItemStatus.AWAITING},
                    synchronize_session=False,
                )
            )

            for model in (WorkOrder, WorkItem):
                (
                    db.query(model)
                    .filter(
                        model.order_id == order.id,
                        model.ended_at.is_(None),
                        model.is_deleted.is_(False),
                    )
                    .update(
                        {
                            model.time_to_produced_secs: None,
                            model.is_deleted: True,
                        },
                        synchronize_session=False,
                    )
                )

            (
                db.query(OrderItemBreak)
                .filter(
                    OrderItemBreak.order_id == order.id,
                    OrderItemBreak.is_deleted.is_(False),
                )
                .update(
                    {OrderItemBreak.is_deleted: True},
                    synchronize_session=False,
                )
            )

            AuditService.log(
                db=db,
                action="order:cancel",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=f"Pedido #{order.id} cancelado",
            )

        db.refresh(order)
        return order
