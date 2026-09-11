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


class UserRefSchema(BaseModel):
    """Referência mínima a um usuário, para exibir autoria."""

    id: int
    username: str
    full_name: str

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
    # Liberação para produzir: Awaiting, Approved ou Recused.
    production_approval: str
    scheduled_date: date
    client_id: int
    client: ClientRefSchema | None = None
    created_by_user_id: int | None = None
    # quem registrou o pedido — a tela de detalhe mostra o nome, não o id
    created_by: UserRefSchema | None = None

    payment_method: str
    is_paid: bool
    total_amount: Decimal

    # Todos os itens do pedido, em qualquer status. É o que as telas de
    # detalhe (admin, vendedor, fiscal) devem consumir.
    items: list[OrderItemResponse]

    # Recorte para a tela do produtor, que trabalha um item por vez.
    produced_items: list[OrderItemResponse]
    current_item: OrderItemResponse | None
    total_items: int

    can_finish: bool

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    id: int
    priority: str
    status: str
    production_approval: str
    scheduled_date: date
    client_id: int
    client: ClientRefSchema

    payment_method: str
    is_paid: bool
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)
