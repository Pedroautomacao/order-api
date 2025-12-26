from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    sku: str
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sku: str
    is_active: bool

    class Config:
        from_attributes = True
