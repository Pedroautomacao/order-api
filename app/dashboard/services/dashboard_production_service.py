from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.orders.enums import OrderStatus
from app.orders.models.work_order import WorkOrder
from app.orders.models.work_item import WorkItem
from app.orders.models.order import Order
from app.dashboard.utils.date_range import (
    resolve_date_range,
    resolve_datetime_range,
)


class DashboardProductionService:
    @staticmethod
    def get(
        db: Session,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        start_date, end_date = resolve_date_range(date_from, date_to)
        # Colunas DateTime precisam do dia inteiro; com `date` os dois limites
        # colapsam na meia-noite e o BETWEEN nao casa com nada.
        start_dt, end_dt = resolve_datetime_range(date_from, date_to)

        avg_order_time = (
            db.query(func.avg(WorkOrder.time_to_produced_secs))
            .filter(
                WorkOrder.is_deleted.is_(False),
                WorkOrder.started_at.between(start_dt, end_dt),
                WorkOrder.time_to_produced_secs.isnot(None),
            )
            .scalar()
            or 0
        )

        avg_item_time = (
            db.query(func.avg(WorkItem.time_to_produced_secs))
            .filter(
                WorkItem.is_deleted.is_(False),
                WorkItem.started_at.between(start_dt, end_dt),
                WorkItem.time_to_produced_secs.isnot(None),
            )
            .scalar()
            or 0
        )

        producing_now = (
            db.query(func.count(Order.id))
            .filter(Order.status == OrderStatus.PRODUCING)
            .scalar()
        )

        production_by_user = (
            db.query(
                WorkOrder.user_id,
                func.count(WorkOrder.id),
                func.avg(WorkOrder.time_to_produced_secs),
            )
            .filter(
                WorkOrder.is_deleted.is_(False),
                WorkOrder.started_at.between(start_dt, end_dt),
                WorkOrder.time_to_produced_secs.isnot(None),
            )
            .group_by(WorkOrder.user_id)
            .all()
        )

        return {
            "avg_order_time_secs": round(avg_order_time, 2),
            "avg_item_time_secs": round(avg_item_time, 2),
            "producing_now": producing_now,
            "production_by_user": [
                {
                    "user_id": user_id,
                    "total_orders": total,
                    "avg_time_secs": round(avg or 0, 2),
                }
                for user_id, total, avg in production_by_user
            ],
        }
