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

    model_config = ConfigDict(from_attributes=True)

