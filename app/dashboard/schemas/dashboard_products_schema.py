from pydantic import BaseModel


class ProductDashboardItem(BaseModel):
    product_id: int
    product_name: str

    total_orders: int
    total_produced_quantity: float
    total_break_quantity: float
    break_rate_percent: float

    avg_item_production_time_secs: float
    total_productions: int
    producing_now: bool


class DashboardProductsResponse(BaseModel):
    products: list[ProductDashboardItem]
