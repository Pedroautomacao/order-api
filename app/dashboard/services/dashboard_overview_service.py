from datetime import date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.orders.enums import OrderStatus, ProductionApproval
from app.orders.models.order import Order
from app.dashboard.utils.date_range import resolve_date_range
from app.core.time import today_sp


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

        # Billed ja passou por Produced: sem soma-lo a taxa de conclusao cai
        # conforme o fiscal fatura. Cancelado sai da base, nao e trabalho
        # pendente.
        concluded_orders = produced_orders + orders_by_status[OrderStatus.BILLED]
        considered_orders = total_orders - orders_by_status[OrderStatus.CANCELED]

        completion_rate = (
            (concluded_orders / considered_orders) * 100
            if considered_orders > 0
            else 0
        )

        producing_now = orders_by_status[OrderStatus.PRODUCING]

        overdue_orders = (
            db.query(func.count(Order.id))
            .filter(
                Order.scheduled_date < start_date,
                # sem CANCELED aqui, pedido cancelado conta como atrasado
                # para sempre
                Order.status.notin_(
                    [
                        OrderStatus.PRODUCED,
                        OrderStatus.BILLED,
                        OrderStatus.CANCELED,
                    ]
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

        # Fila parada por falta de liberação. Não filtra por data: um pedido
        # esquecido sem aprovação é justamente o que precisa aparecer.
        awaiting_production_approval = (
            db.query(func.count(Order.id))
            .filter(
                Order.production_approval == ProductionApproval.AWAITING,
                Order.status == OrderStatus.AWAITING,
                Order.is_deleted.is_(False),
            )
            .scalar()
        )

        # Pedidos por dia — últimos 7 dias (por data de entrega), incluindo dias vazios
        days = [today_sp() - timedelta(days=i) for i in range(6, -1, -1)]
        rows = (
            db.query(Order.scheduled_date, func.count(Order.id))
            .filter(
                Order.scheduled_date.between(days[0], days[-1]),
                Order.is_deleted.is_(False),
            )
            .group_by(Order.scheduled_date)
            .all()
        )
        by_day_map = {d: 0 for d in days}
        for d, count in rows:
            if d in by_day_map:
                by_day_map[d] = count
        orders_by_day = [
            {"date": d.isoformat(), "count": by_day_map[d]} for d in days
        ]

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
            "awaiting_production_approval": awaiting_production_approval,
            "orders_by_day": orders_by_day,
        }
