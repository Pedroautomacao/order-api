from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.units.schemas.unit_schema import UnitResponse


class ProductBase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    name: str
    description: str | None = None
    sku: str

    unit_price: Decimal = Field(
        default=0,
        alias="unitPrice",
        ge=0,
        description="Preço unitário de venda",
    )

    unit_of_measure_id: int = Field(
        ...,
        alias="unitOfMeasureId",
    )

    is_active: bool = Field(
        default=True,
        alias="isActive",
    )



class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    name: str | None = None
    description: str | None = None

    unit_price: Decimal | None = Field(
        default=None,
        alias="unitPrice",
        ge=0,
    )

    unit_of_measure_id: int | None = Field(
        default=None,
        alias="unitOfMeasureId",
    )

    is_active: bool | None = Field(
        default=None,
        alias="isActive",
    )


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sku: str
    is_active: bool
    unit_price: Decimal

    unit: UnitResponse

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

