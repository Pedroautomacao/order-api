from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    name: str
    priority: str = Field(
        ...,
        min_length=1,
        max_length=1,
        pattern="^[B-Z]$",
        description="Client priority from B to Z",
    )
    cpf_cnpj: str
    address: str
    phone_number: str
    observations: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    priority: str | None = Field(
        default=None,
        min_length=1,
        max_length=1,
        pattern="^[B-Z]$",
    )
    address: str | None = None
    phone_number: str | None = None
    observations: str | None = None


class ClientResponse(BaseModel):
    id: int
    name: str
    priority: str
    cpf_cnpj: str
    address: str
    phone_number: str
    observations: str | None

    class Config:
        from_attributes = True
