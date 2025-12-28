from pydantic import BaseModel


class ClientDashboardItem(BaseModel):
    client_id: int
    client_name: str

    total_orders: int
    produced_orders: int
    billed_orders: int
    canceled_orders: int
    producing_now: int

    completion_rate_percent: float
    total_break_quantity: float
    break_rate_percent: float
    avg_production_time_secs: float


class DashboardClientsResponse(BaseModel):
    clients: list[ClientDashboardItem]
