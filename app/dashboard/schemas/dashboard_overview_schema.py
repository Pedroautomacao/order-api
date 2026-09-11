from pydantic import BaseModel


class OrdersByStatus(BaseModel):
    awaiting: int
    producing: int
    produced: int
    billed: int
    canceled: int


class OrdersByDayPoint(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class DashboardOverviewResponse(BaseModel):
    orders_today: OrdersByStatus
    producing_now: int
    completion_rate_today: float
    overdue_orders: int
    produced_not_billed: int
    # Pedidos travados esperando alguém liberar a produção.
    awaiting_production_approval: int = 0
    orders_by_day: list[OrdersByDayPoint] = []
