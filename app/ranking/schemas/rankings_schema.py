from pydantic import BaseModel


class RankingItem(BaseModel):
    id: int
    name: str
    value: float


class RankingsResponse(BaseModel):
    top_products_by_volume: list[RankingItem]
    top_products_by_breaks: list[RankingItem]
    top_products_by_time: list[RankingItem]

    top_clients_by_orders: list[RankingItem]
    top_clients_by_breaks: list[RankingItem]
    top_clients_by_delays: list[RankingItem]
