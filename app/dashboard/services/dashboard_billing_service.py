from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.dashboard.utils.date_range import resolve_date_range


class DashboardBillingService:
    @staticmethod
    def get(
        db: Session,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        start_date, end_date = resolve_date_range(date_from, date_to)

        produced = (
            db.query(func.count(Order.id))
            .filter(
                Order.status == OrderStatus.PRODUCED,
                Order.updated_at.between(start_date, end_date),
            )
            .scalar()
        )

        billed = (
            db.query(func.count(Order.id))
            .filter(
                Order.status == OrderStatus.BILLED,
                Order.updated_at.between(start_date, end_date),
            )
            .scalar()
        )

        rate = (billed / produced * 100) if produced > 0 else 0

        return {
            "produced_orders": produced,
            "billed_orders": billed,
            "billing_rate_percent": round(rate, 2),
        }
