from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.clients.models import Client
from app.order_item_breaks.models import OrderItemBreak
from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.orders.models.work_order import WorkOrder
from app.dashboard.utils.date_range import resolve_date_range


class DashboardClientsService:
    @staticmethod
    def get(
        db: Session,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        start_date, end_date = resolve_date_range(date_from, date_to)

        clients = (
            db.query(Client)
            .filter(Client.is_deleted.is_(False))
            .order_by(Client.name)
            .all()
        )

        response = []

        for client in clients:
            total_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.client_id == client.id,
                    Order.scheduled_date.between(start_date, end_date),
                    Order.is_deleted.is_(False),
                )
                .scalar()
            )

            produced_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.client_id == client.id,
                    Order.status == OrderStatus.PRODUCED,
                    Order.scheduled_date.between(start_date, end_date),
                )
                .scalar()
            )

            billed_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.client_id == client.id,
                    Order.status == OrderStatus.BILLED,
                    Order.scheduled_date.between(start_date, end_date),
                )
                .scalar()
            )

            canceled_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.client_id == client.id,
                    Order.status == OrderStatus.CANCELED,
                    Order.scheduled_date.between(start_date, end_date),
                )
                .scalar()
            )

            producing_now = (
                db.query(func.count(Order.id))
                .filter(
                    Order.client_id == client.id,
                    Order.status == OrderStatus.PRODUCING,
                )
                .scalar()
            )

            completion_rate = (
                (produced_orders / total_orders) * 100
                if total_orders > 0
                else 0
            )

            # Quebras do cliente
            total_break = (
                db.query(func.sum(OrderItemBreak.difference_quantity))
                .join(
                    Order,
                    Order.id == OrderItemBreak.order_id,
                )
                .filter(
                    Order.client_id == client.id,
                    OrderItemBreak.created_at.between(
                        start_date, end_date
                    ),
                )
                .scalar()
                or 0
            )

            expected_quantity = (
                db.query(func.sum(OrderItemBreak.expected_quantity))
                .join(
                    Order,
                    Order.id == OrderItemBreak.order_id,
                )
                .filter(
                    Order.client_id == client.id,
                    OrderItemBreak.created_at.between(
                        start_date, end_date
                    ),
                )
                .scalar()
                or 0
            )

            break_rate = (
                (total_break / expected_quantity) * 100
                if expected_quantity > 0
                else 0
            )

            avg_production_time = (
                db.query(func.avg(WorkOrder.time_to_produced_secs))
                .join(
                    Order,
                    Order.id == WorkOrder.order_id,
                )
                .filter(
                    Order.client_id == client.id,
                    WorkOrder.started_at.between(
                        start_date, end_date
                    ),
                )
                .scalar()
                or 0
            )

            response.append(
                {
                    "client_id": client.id,
                    "client_name": client.name,
                    "total_orders": total_orders,
                    "produced_orders": produced_orders,
                    "billed_orders": billed_orders,
                    "canceled_orders": canceled_orders,
                    "producing_now": producing_now,
                    "completion_rate_percent": round(
                        completion_rate, 2
                    ),
                    "total_break_quantity": float(total_break),
                    "break_rate_percent": round(break_rate, 2),
                    "avg_production_time_secs": round(
                        avg_production_time, 2
                    ),
                }
            )

        return {"clients": response}
