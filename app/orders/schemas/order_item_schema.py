from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.products.schemas.product_schema import ProductResponse


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    product_id: int = Field(
        ...,
        alias="productId",
    )

    quantity: float = Field(gt=0)

    # Preço exclusivo deste pedido. Vazio = usa o preço de tabela do produto.
    unit_price: Decimal | None = Field(
        default=None,
        alias="unitPrice",
        ge=0,
        description="Preço unitário cobrado neste pedido",
    )


class OrderItemConfirm(BaseModel):
    produced_quantity: float = Field(
        gt=0,
        description="Real produced quantity",
        alias="producedQuantity",
    )


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: float
    produced_quantity: float | None
    status: str
    product: ProductResponse

    # Congelado na criação do pedido; não acompanha mudança de preço do produto
    unit_price: Decimal
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)

