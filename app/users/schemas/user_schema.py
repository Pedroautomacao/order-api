from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.users.schemas.role_schema import RoleResponse


class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    cpf: str
    email: EmailStr | None = None
    is_active: bool = True


class UserCreate(UserBase):
    model_config = ConfigDict(populate_by_name=True)

    password: str
    role_ids: list[int] = Field(default_factory=list, alias="roleIds")


class UserUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    role_ids: list[int] | None = Field(default=None, alias="roleIds")


class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    cpf: str
    email: EmailStr | None
    is_active: bool
    roles: list["RoleResponse"] = []

    class Config:
        from_attributes = True


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)
