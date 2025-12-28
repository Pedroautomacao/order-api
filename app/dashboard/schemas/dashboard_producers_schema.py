from pydantic import BaseModel


class ProducerDashboardItem(BaseModel):
    user_id: int
    username: str

    producing_now: bool
    total_finished_orders: int
    avg_order_time_secs: float

    total_items_produced: int
    avg_item_time_secs: float

    total_break_quantity: float
    break_rate_percent: float

    productivity_orders_per_day: float


class DashboardProducersResponse(BaseModel):
    producers: list[ProducerDashboardItem]
