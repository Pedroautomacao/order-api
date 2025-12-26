from pydantic import BaseModel, Field, ConfigDict


class UnitBase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    code: str
    name: str
    description: str | None = None

    is_active: bool = Field(
        default=True,
        alias="isActive",
    )


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    name: str | None = None
    description: str | None = None

    is_active: bool | None = Field(
        default=None,
        alias="isActive",
    )


class UnitResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )
