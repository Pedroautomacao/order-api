from pydantic import BaseModel, Field, ConfigDict


class ClientBase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    name: str

    priority: str = Field(
        ...,
        min_length=1,
        max_length=1,
        pattern="^[B-Z]$",
        description="Client priority from B to Z",
    )

    cpf_cnpj: str = Field(
        ...,
        alias="cpfCnpj",
    )

    address: str

    phone_number: str = Field(
        ...,
        alias="phoneNumber",
    )

    observations: str | None = None
    is_active: bool = Field(True, alias="isActive")


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )

    name: str | None = None

    priority: str | None = Field(
        default=None,
        min_length=1,
        max_length=1,
        pattern="^[B-Z]$",
    )

    address: str | None = None

    phone_number: str | None = Field(
        default=None,
        alias="phoneNumber",
    )

    observations: str | None = None
    is_active: bool | None = Field(None, alias="isActive")


class ClientResponse(BaseModel):
    id: int
    name: str
    priority: str
    cpf_cnpj: str
    address: str
    phone_number: str
    observations: str | None
    is_active: bool

    class Config:
        from_attributes = True
