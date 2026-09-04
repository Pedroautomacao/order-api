from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.users.models.user import User
from app.orders.models.order import Order
from app.orders.models.work_order import WorkOrder
from app.orders.models.work_item import WorkItem
from app.orders.enums import OrderStatus
from app.order_item_breaks.models import OrderItemBreak
from app.dashboard.utils.date_range import (
    resolve_date_range,
    resolve_datetime_range,
)


class DashboardProducersService:
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
        days_range = max((end_date - start_date).days + 1, 1)

        producers = (
            db.query(User)
            .filter(User.is_deleted.is_(False))
            .order_by(User.username)
            .all()
        )

        response = []

        for user in producers:
            producing_now = (
                db.query(func.count(Order.id))
                .filter(
                    Order.assigned_user_id == user.id,
                    Order.status == OrderStatus.PRODUCING,
                )
                .scalar()
                > 0
            )

            total_finished_orders = (
                db.query(func.count(WorkOrder.id))
                .filter(
                    WorkOrder.user_id == user.id,
                    WorkOrder.is_deleted.is_(False),
                    WorkOrder.time_to_produced_secs.isnot(None),
                    WorkOrder.started_at.between(
                        start_dt, end_dt
                    ),
                )
                .scalar()
            )

            avg_order_time = (
                db.query(func.avg(WorkOrder.time_to_produced_secs))
                .filter(
                    WorkOrder.user_id == user.id,
                    WorkOrder.is_deleted.is_(False),
                    WorkOrder.time_to_produced_secs.isnot(None),
                    WorkOrder.started_at.between(
                        start_dt, end_dt
                    ),
                )
                .scalar()
                or 0
            )

            total_items_produced = (
                db.query(func.count(WorkItem.id))
                .filter(
                    WorkItem.user_id == user.id,
                    # apontamento de ciclo resetado nao conta como producao
                    WorkItem.is_deleted.is_(False),
                    WorkItem.ended_at.isnot(None),
                    WorkItem.started_at.between(
                        start_dt, end_dt
                    ),
                )
                .scalar()
            )

            avg_item_time = (
                db.query(func.avg(WorkItem.time_to_produced_secs))
                .filter(
                    WorkItem.user_id == user.id,
                    WorkItem.is_deleted.is_(False),
                    WorkItem.time_to_produced_secs.isnot(None),
                    WorkItem.started_at.between(
                        start_dt, end_dt
                    ),
                )
                .scalar()
                or 0
            )

            total_break_quantity = (
                db.query(func.sum(OrderItemBreak.difference_quantity))
                .join(
                    WorkItem,
                    WorkItem.order_item_id == OrderItemBreak.order_item_id,
                )
                .filter(
                    WorkItem.user_id == user.id,
                    OrderItemBreak.is_deleted.is_(False),
                    OrderItemBreak.created_at.between(
                        start_dt, end_dt
                    ),
                )
                .scalar()
                or 0
            )

            expected_quantity = (
                db.query(func.sum(OrderItemBreak.expected_quantity))
                .join(
                    WorkItem,
                    WorkItem.order_item_id == OrderItemBreak.order_item_id,
                )
                .filter(
                    WorkItem.user_id == user.id,
                    OrderItemBreak.is_deleted.is_(False),
                    OrderItemBreak.created_at.between(
                        start_dt, end_dt
                    ),
                )
                .scalar()
                or 0
            )

            break_rate = (
                (total_break_quantity / expected_quantity) * 100
                if expected_quantity > 0
                else 0
            )

            productivity = (
                total_finished_orders / days_range
                if days_range > 0
                else 0
            )

            response.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "producing_now": producing_now,
                    "total_finished_orders": total_finished_orders,
                    "avg_order_time_secs": round(
                        avg_order_time, 2
                    ),
                    "total_items_produced": total_items_produced,
                    "avg_item_time_secs": round(
                        avg_item_time, 2
                    ),
                    "total_break_quantity": float(
                        total_break_quantity
                    ),
                    "break_rate_percent": round(
                        break_rate, 2
                    ),
                    "productivity_orders_per_day": round(
                        productivity, 2
                    ),
                }
            )

        return {"producers": response}
