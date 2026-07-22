from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict
from typing import List

from app.orders.enums import PaymentMethod
from app.orders.schemas.order_item_schema import OrderItemCreate, OrderItemResponse


class ClientRefSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


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

    payment_method: PaymentMethod = Field(
        PaymentMethod.CASH,
        alias="paymentMethod",
        description="Cash (à vista) ou Credit (a prazo)",
    )

    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
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

    payment_method: PaymentMethod = Field(
        PaymentMethod.CASH,
        alias="paymentMethod",
    )

    items: List[OrderItemCreate]


class OrderResponse(BaseModel):
    id: int
    priority: str
    status: str
    scheduled_date: date
    client: ClientRefSchema | None = None
    created_by_user_id: int | None = None

    payment_method: str
    is_paid: bool
    total_amount: Decimal

    produced_items: list[OrderItemResponse]
    current_item: OrderItemResponse | None
    total_items: int

    can_finish: bool

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    id: int
    priority: str
    status: str
    scheduled_date: date
    client_id: int
    client: ClientRefSchema

    payment_method: str
    is_paid: bool
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)
