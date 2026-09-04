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

        # Recorte por data de entrega, como todos os outros painéis de pedido.
        # updated_at é NULL enquanto o pedido nunca foi atualizado e muda de
        # bucket a cada edição posterior (marcar como pago, remarcar data).
        produced = (
            db.query(func.count(Order.id))
            .filter(
                Order.status == OrderStatus.PRODUCED,
                Order.scheduled_date.between(start_date, end_date),
                Order.is_deleted.is_(False),
            )
            .scalar()
        )

        billed = (
            db.query(func.count(Order.id))
            .filter(
                Order.status == OrderStatus.BILLED,
                Order.scheduled_date.between(start_date, end_date),
                Order.is_deleted.is_(False),
            )
            .scalar()
        )

        # Produced e Billed sao estados excludentes e a transicao e de mao
        # unica: dividir so por `produced` tira do denominador exatamente o
        # que entrou no numerador — a taxa passava de 100% e desabava para 0%
        # quando tudo era faturado.
        reached_production = produced + billed
        rate = (
            (billed / reached_production * 100)
            if reached_production > 0
            else 0
        )

        return {
            "produced_orders": produced,
            "billed_orders": billed,
            "billing_rate_percent": round(rate, 2),
        }
