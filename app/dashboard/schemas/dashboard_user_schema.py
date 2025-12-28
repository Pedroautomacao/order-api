from pydantic import BaseModel


class UserProductionStats(BaseModel):
    user_id: int
    producing_now: bool
    total_orders: int
    avg_order_time_secs: float


class DashboardUsersResponse(BaseModel):
    producing_users: int
    idle_users: int
    users: list[UserProductionStats]
