from pydantic import BaseModel


class ProductionByUser(BaseModel):
    user_id: int
    total_orders: int
    avg_time_secs: float


class DashboardProductionResponse(BaseModel):
    avg_order_time_secs: float
    avg_item_time_secs: float
    producing_now: int
    production_by_user: list[ProductionByUser]
