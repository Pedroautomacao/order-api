from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.order_item_breaks.models import OrderItemBreak
from app.orders.enums import OrderStatus
from app.products.models.product import Product
from app.clients.models import Client
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.models.work_item import WorkItem
from app.dashboard.utils.date_range import resolve_date_range


class RankingsService:
    @staticmethod
    def get(
        db: Session,
        *,
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        start_date, end_date = resolve_date_range(date_from, date_to)

        # ================= PRODUCTS =================

        top_products_by_volume = (
            db.query(
                Product.id,
                Product.name,
                func.sum(OrderItem.produced_quantity).label("value"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id)
            .order_by(desc("value"))
            .limit(limit)
            .all()
        )

        top_products_by_breaks = (
            db.query(
                Product.id,
                Product.name,
                func.sum(OrderItemBreak.difference_quantity).label("value"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(
                OrderItemBreak,
                OrderItemBreak.order_item_id == OrderItem.id,
            )
            .filter(
                OrderItemBreak.created_at.between(start_date, end_date)
            )
            .group_by(Product.id)
            .order_by(desc("value"))
            .limit(limit)
            .all()
        )

        top_products_by_time = (
            db.query(
                Product.id,
                Product.name,
                func.avg(WorkItem.time_to_produced_secs).label("value"),
            )
            .join(WorkItem, WorkItem.product_id == Product.id)
            .filter(
                WorkItem.time_to_produced_secs.isnot(None),
                WorkItem.started_at.between(start_date, end_date),
            )
            .group_by(Product.id)
            .order_by(desc("value"))
            .limit(limit)
            .all()
        )

        # ================= CLIENTS =================

        top_clients_by_orders = (
            db.query(
                Client.id,
                Client.name,
                func.count(Order.id).label("value"),
            )
            .join(Order, Order.client_id == Client.id)
            .filter(
                Order.scheduled_date.between(start_date, end_date)
            )
            .group_by(Client.id)
            .order_by(desc("value"))
            .limit(limit)
            .all()
        )

        top_clients_by_breaks = (
            db.query(
                Client.id,
                Client.name,
                func.sum(OrderItemBreak.difference_quantity).label("value"),
            )
            .join(Order, Order.client_id == Client.id)
            .join(
                OrderItemBreak,
                OrderItemBreak.order_id == Order.id,
            )
            .filter(
                OrderItemBreak.created_at.between(start_date, end_date)
            )
            .group_by(Client.id)
            .order_by(desc("value"))
            .limit(limit)
            .all()
        )

        top_clients_by_delays = (
            db.query(
                Client.id,
                Client.name,
                func.count(Order.id).label("value"),
            )
            .join(Order, Order.client_id == Client.id)
            .filter(
                Order.scheduled_date < start_date,
                Order.status.notin_(
                    [OrderStatus.PRODUCED, OrderStatus.BILLED]
                ),
            )
            .group_by(Client.id)
            .order_by(desc("value"))
            .limit(limit)
            .all()
        )

        def serialize(rows):
            return [
                {"id": i, "name": n, "value": float(v or 0)}
                for i, n, v in rows
            ]

        return {
            "top_products_by_volume": serialize(
                top_products_by_volume
            ),
            "top_products_by_breaks": serialize(
                top_products_by_breaks
            ),
            "top_products_by_time": serialize(
                top_products_by_time
            ),
            "top_clients_by_orders": serialize(
                top_clients_by_orders
            ),
            "top_clients_by_breaks": serialize(
                top_clients_by_breaks
            ),
            "top_clients_by_delays": serialize(
                top_clients_by_delays
            ),
        }
