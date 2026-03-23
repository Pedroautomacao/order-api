from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.core.services.base_atomic_service import BaseAtomicService
from app.core.time import utcnow
from app.order_item_breaks.models import OrderItemBreak
from app.orders.dependencies import get_order_item_or_404
from app.orders.enums import OrderItemStatus
from app.orders.exception_handler import OrderNotAssignedToUserException, InvalidOrderItemStateException
from app.orders.models.work_item import WorkItem
from app.orders.repositories.work_item_repository import get_open_work_item
from app.orders.utils.resolve_current_item import resolve_current_item


class OrderItemService(BaseAtomicService):
    @staticmethod
    def confirm_item(
            db: Session,
            *,
            order_item_id: int,
            data,
            current_user,
    ):
        item = get_order_item_or_404(db, order_item_id)
        order = item.order

        if order.assigned_user_id != current_user.id:
            raise OrderNotAssignedToUserException()

        if item.status != OrderItemStatus.PRODUCING:
            raise InvalidOrderItemStateException(
                item.id,
                OrderItemStatus.PRODUCING,
                item.status,
            )

        expected = item.quantity
        if data.produced_quantity < expected:
            db.add(
                OrderItemBreak(
                    order_id=item.order_id,
                    order_item_id=item.id,
                    expected_quantity=expected,
                    confirmed_quantity=data.produced_quantity,
                    difference_quantity=expected - data.produced_quantity,
                    created_by=current_user.id,
                )
            )

        # salvar quantidade produzida
        item.produced_quantity = data.produced_quantity
        item.status = OrderItemStatus.PRODUCED

        # fechar work_item aberto
        work_item = get_open_work_item(
            db=db,
            order_id=order.id,
            product_id=item.product_id,
            user_id=current_user.id,
        )

        work_item.ended_at = utcnow()
        work_item.time_to_produced_secs = (work_item.ended_at - work_item.started_at).seconds

        # iniciar próximo item
        next_item = resolve_current_item(order)
        if next_item:
            next_item.status = OrderItemStatus.PRODUCING

            db.add(
                WorkItem(
                    order_id=order.id,
                    product_id=next_item.product_id,
                    user_id=current_user.id,
                    started_at=utcnow(),
                    order_item_id=next_item.id
                )
            )

        AuditService.log(
            db=db,
            action="order:item_confirm",
            entity="order_item",
            entity_id=item.id,
            user_id=current_user.id,
            description=f"Produced {data.produced_quantity}",
        )

        return order

    @staticmethod
    def update_produced_quantity(
            db: Session,
            *,
            order_item_id: int,
            data,
            current_user,
    ):
        item = get_order_item_or_404(db, order_item_id)
        order = item.order

        if order.assigned_user_id != current_user.id:
            raise OrderNotAssignedToUserException()

        if item.status != OrderItemStatus.PRODUCED:
            raise InvalidOrderItemStateException(
                item.id,
                OrderItemStatus.PRODUCED,
                item.status,
            )

        old_qty = item.produced_quantity
        new_qty = data.produced_quantity

        # Remove break existente e recria se necessário
        db.query(OrderItemBreak).filter(
            OrderItemBreak.order_item_id == item.id
        ).delete()

        if new_qty < item.quantity:
            db.add(
                OrderItemBreak(
                    order_id=item.order_id,
                    order_item_id=item.id,
                    expected_quantity=item.quantity,
                    confirmed_quantity=new_qty,
                    difference_quantity=item.quantity - new_qty,
                    created_by=current_user.id,
                )
            )

        item.produced_quantity = new_qty

        AuditService.log(
            db=db,
            action="order:item_update_quantity",
            entity="order_item",
            entity_id=item.id,
            user_id=current_user.id,
            description=f"Updated produced qty from {old_qty} to {new_qty}",
        )

        return order
