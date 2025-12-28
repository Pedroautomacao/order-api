from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.dashboard.utils.date_range import resolve_date_range


class DashboardService:
    @staticmethod
    def overview(
        db: Session,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        start_date, end_date = resolve_date_range(date_from, date_to)

        orders_by_status = {
            OrderStatus.AWAITING: 0,
            OrderStatus.PRODUCING: 0,
            OrderStatus.PRODUCED: 0,
            OrderStatus.BILLED: 0,
            OrderStatus.CANCELED: 0,
        }

        for status, count in (
            db.query(Order.status, func.count(Order.id))
            .filter(
                Order.scheduled_date.between(start_date, end_date),
                Order.is_deleted.is_(False),
            )
            .group_by(Order.status)
            .all()
        ):
            orders_by_status[status] = count

        total_orders = sum(orders_by_status.values())
        produced_orders = orders_by_status[OrderStatus.PRODUCED]

        completion_rate = (
            (produced_orders / total_orders) * 100
            if total_orders > 0
            else 0
        )

        producing_now = orders_by_status[OrderStatus.PRODUCING]

        overdue_orders = (
            db.query(func.count(Order.id))
            .filter(
                Order.scheduled_date < start_date,
                Order.status.notin_(
                    [OrderStatus.PRODUCED, OrderStatus.BILLED]
                ),
                Order.is_deleted.is_(False),
            )
            .scalar()
        )

        produced_not_billed = (
            db.query(func.count(Order.id))
            .filter(
                Order.status == OrderStatus.PRODUCED,
                Order.is_deleted.is_(False),
            )
            .scalar()
        )

        return {
            "orders_today": {
                "awaiting": orders_by_status[OrderStatus.AWAITING],
                "producing": orders_by_status[OrderStatus.PRODUCING],
                "produced": orders_by_status[OrderStatus.PRODUCED],
                "billed": orders_by_status[OrderStatus.BILLED],
                "canceled": orders_by_status[OrderStatus.CANCELED],
            },
            "producing_now": producing_now,
            "completion_rate_today": round(completion_rate, 2),
            "overdue_orders": overdue_orders,
            "produced_not_billed": produced_not_billed,
        }
