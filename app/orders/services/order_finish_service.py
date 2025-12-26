from datetime import datetime

from app.core.services.base_atomic_service import BaseAtomicService
from app.core.time import utcnow
from app.orders.enums import OrderStatus
from app.audit.services.audit_service import AuditService
from app.orders.exception_handler import OrderNotFinishedException


class OrderFinishService(BaseAtomicService):
    @staticmethod
    def finish_order(
        db,
        *,
        order,
        current_user,
    ):

        if any(i.status != "Produced" for i in order.items):
            raise OrderNotFinishedException()

        order.status = OrderStatus.PRODUCED

        work_order = order.work_order
        work_order.ended_at = utcnow()
        work_order.time_to_produced_secs = (
            work_order.ended_at - work_order.started_at
        ).seconds

        AuditService.log(
            db=db,
            action="order:finish",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=f"Order {order.id} finished",
        )

        db.refresh(order)
        return order
