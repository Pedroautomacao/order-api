from pydantic import BaseModel


class BreakByProduct(BaseModel):
    product_id: int
    total_lost: float


class DashboardBreaksResponse(BaseModel):
    total_lost_quantity: float
    break_rate_percent: float
    breaks_by_product: list[BreakByProduct]
