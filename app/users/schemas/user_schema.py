from pydantic import BaseModel, EmailStr, Field

from app.users.schemas.role_schema import RoleResponse


class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    cpf: str
    email: EmailStr | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


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
