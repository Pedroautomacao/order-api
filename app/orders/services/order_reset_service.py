from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.order_item_breaks.models import OrderItemBreak
from app.orders.models.work_order import WorkOrder
from app.orders.models.work_item import WorkItem


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

        with atomic(db):
            # Reset order
            order.status = OrderStatus.AWAITING
            order.assigned_user_id = None

            # Reset order items
            (
                db.query(OrderItem)
                .filter(OrderItem.order_id == order.id)
                .update(
                    {
                        OrderItem.status: OrderItemStatus.AWAITING,
                        OrderItem.produced_quantity: 0,
                    },
                    synchronize_session=False,
                )
            )

            # O ciclo de produção anterior deixa de valer: zera os tempos (para
            # não entrarem nas médias) e marca os apontamentos como excluídos.
            # Sem isso eles continuam "abertos" e o próximo ciclo fecha o
            # registro errado, já que a re-atribuição cria apontamentos novos.
            for model in (WorkOrder, WorkItem):
                (
                    db.query(model)
                    .filter(
                        model.order_id == order.id,
                        model.is_deleted.is_(False),
                    )
                    .update(
                        {
                            model.ended_at: None,
                            model.time_to_produced_secs: None,
                            model.is_deleted: True,
                        },
                        synchronize_session=False,
                    )
                )

            # As quebras apontadas no ciclo anulado tambem deixam de valer:
            # ao reproduzir, confirm_item cria um registro novo e o mesmo
            # item apareceria duas vezes no painel de quebras.
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
                action="order:reset_production",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=f"Order {order.id} reset by {current_user.username}",
            )

        db.refresh(order)
        return order
