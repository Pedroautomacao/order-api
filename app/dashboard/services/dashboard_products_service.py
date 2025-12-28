from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.order_item_breaks.models import OrderItemBreak
from app.products.models.product import Product
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.models.work_item import WorkItem
from app.dashboard.utils.date_range import resolve_date_range


class DashboardProductsService:
    @staticmethod
    def get(
        db: Session,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        start_date, end_date = resolve_date_range(date_from, date_to)

        products = (
            db.query(Product)
            .filter(Product.is_deleted.is_(False))
            .order_by(Product.name)
            .all()
        )

        response = []

        for product in products:
            # Total de pedidos que possuem esse produto
            total_orders = (
                db.query(func.count(distinct(OrderItem.order_id)))
                .join(
                    Order,
                    Order.id == OrderItem.order_id,
                )
                .filter(
                    OrderItem.product_id == product.id,
                    Order.scheduled_date.between(start_date, end_date),
                    Order.is_deleted.is_(False),
                )
                .scalar()
            )

            # Quantidade produzida
            total_produced_quantity = (
                db.query(func.sum(OrderItem.produced_quantity))
                .filter(
                    OrderItem.product_id == product.id,
                )
                .scalar()
                or 0
            )

            # Quebras
            total_break_quantity = (
                db.query(func.sum(OrderItemBreak.difference_quantity))
                .join(
                    OrderItem,
                    OrderItem.id == OrderItemBreak.order_item_id,
                )
                .filter(
                    OrderItem.product_id == product.id,
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
                    OrderItem,
                    OrderItem.id == OrderItemBreak.order_item_id,
                )
                .filter(
                    OrderItem.product_id == product.id,
                    OrderItemBreak.created_at.between(
                        start_date, end_date
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

            # Produções (work items)
            total_productions = (
                db.query(func.count(WorkItem.id))
                .filter(
                    WorkItem.product_id == product.id,
                    WorkItem.started_at.between(
                        start_date, end_date
                    ),
                )
                .scalar()
            )

            avg_item_time = (
                db.query(func.avg(WorkItem.time_to_produced_secs))
                .filter(
                    WorkItem.product_id == product.id,
                    WorkItem.time_to_produced_secs.isnot(None),
                    WorkItem.started_at.between(
                        start_date, end_date
                    ),
                )
                .scalar()
                or 0
            )

            producing_now = (
                db.query(func.count(WorkItem.id))
                .filter(
                    WorkItem.product_id == product.id,
                    WorkItem.ended_at.is_(None),
                )
                .scalar()
                > 0
            )

            response.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "total_orders": total_orders,
                    "total_produced_quantity": float(
                        total_produced_quantity
                    ),
                    "total_break_quantity": float(
                        total_break_quantity
                    ),
                    "break_rate_percent": round(break_rate, 2),
                    "avg_item_production_time_secs": round(
                        avg_item_time, 2
                    ),
                    "total_productions": total_productions,
                    "producing_now": producing_now,
                }
            )

        return {"products": response}
