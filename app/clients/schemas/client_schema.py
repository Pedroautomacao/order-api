from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, model_validator


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

    # Meios de pagamento aceitos (ao menos um deve ser True)
    allow_cash: bool = Field(True, alias="allowCash")
    allow_credit: bool = Field(True, alias="allowCredit")

    # Limite de crédito a prazo (R$)
    credit_limit: Decimal = Field(0, alias="creditLimit", ge=0)

    @model_validator(mode="after")
    def _at_least_one_payment(self):
        if not self.allow_cash and not self.allow_credit:
            raise ValueError("Selecione pelo menos uma forma de pagamento.")
        return self


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

    allow_cash: bool | None = Field(None, alias="allowCash")
    allow_credit: bool | None = Field(None, alias="allowCredit")
    credit_limit: Decimal | None = Field(None, alias="creditLimit", ge=0)


class ClientResponse(BaseModel):
    id: int
    name: str
    priority: str
    cpf_cnpj: str
    address: str
    phone_number: str
    observations: str | None
    is_active: bool

    allow_cash: bool
    allow_credit: bool
    credit_limit: Decimal

    class Config:
        from_attributes = True


class ClientCreditResponse(BaseModel):
    """Situação de crédito do cliente (usada no formulário de pedido)."""
    client_id: int
    credit_limit: Decimal
    outstanding: Decimal
    available: Decimal
    allow_cash: bool
    allow_credit: bool
