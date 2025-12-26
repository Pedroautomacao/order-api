from datetime import date

from pydantic import BaseModel, Field, ConfigDict
from typing import List

from app.orders.schemas.order_item_schema import OrderItemCreate, OrderItemResponse


class OrderCreate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    client_id: int = Field(
        ...,
        alias="clientId",
    )

    scheduled_date: date = Field(
        ...,
        alias="scheduledDate",
        description="Scheduled delivery date (must be today or future)",
    )

    items: List[OrderItemCreate]


class OrderResponse(BaseModel):
    id: int
    priority: str
    status: str
    scheduled_date: date

    produced_items: list[OrderItemResponse]
    current_item: OrderItemResponse | None

    can_finish: bool

    model_config = ConfigDict(from_attributes=True)
