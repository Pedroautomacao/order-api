from pydantic import BaseModel


class DashboardBillingResponse(BaseModel):
    produced_orders: int
    billed_orders: int
    billing_rate_percent: float
