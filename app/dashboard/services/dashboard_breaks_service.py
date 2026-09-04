from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.order_item_breaks.models import OrderItemBreak
from app.orders.models.order_item import OrderItem
from app.dashboard.utils.date_range import (
    resolve_date_range,
    resolve_datetime_range,
)


class DashboardBreaksService:
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

        total_lost = (
            db.query(func.sum(OrderItemBreak.difference_quantity))
            .filter(
                OrderItemBreak.created_at.between(start_dt, end_dt),
                OrderItemBreak.is_deleted.is_(False),
            )
            .scalar()
            or 0
        )

        total_expected = (
            db.query(func.sum(OrderItemBreak.expected_quantity))
            .filter(
                OrderItemBreak.created_at.between(start_dt, end_dt),
                OrderItemBreak.is_deleted.is_(False),
            )
            .scalar()
            or 0
        )

        break_rate = (
            (total_lost / total_expected) * 100
            if total_expected > 0
            else 0
        )

        by_product = (
            db.query(
                OrderItem.product_id,
                func.sum(OrderItemBreak.difference_quantity),
            )
            .join(
                OrderItem,
                OrderItem.id == OrderItemBreak.order_item_id,
            )
            .filter(
                OrderItemBreak.created_at.between(start_dt, end_dt),
                OrderItemBreak.is_deleted.is_(False),
            )
            .group_by(OrderItem.product_id)
            .all()
        )

        return {
            "total_lost_quantity": float(total_lost),
            "break_rate_percent": round(break_rate, 2),
            "breaks_by_product": [
                {
                    "product_id": product_id,
                    "total_lost": float(total),
                }
                for product_id, total in by_product
            ],
        }
