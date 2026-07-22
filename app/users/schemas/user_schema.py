import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.users.schemas.role_schema import RoleResponse

# Política de senha: mínimo 6 caracteres, ao menos 1 número e 1 caractere especial.
PASSWORD_MIN_LENGTH = 6
_SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")
_DIGIT_RE = re.compile(r"\d")


def validate_password_strength(value: str) -> str:
    if value is None:
        return value
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError("A senha deve ter no mínimo 6 caracteres.")
    if not _DIGIT_RE.search(value):
        raise ValueError("A senha deve conter ao menos um número.")
    if not _SPECIAL_RE.search(value):
        raise ValueError("A senha deve conter ao menos um caractere especial.")
    return value


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

    @field_validator("password")
    @classmethod
    def _check_password(cls, v):
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    password: str | None = None
    role_ids: list[int] | None = Field(default=None, alias="roleIds")

    @field_validator("password")
    @classmethod
    def _check_password(cls, v):
        if v is None or v == "":
            return None
        return validate_password_strength(v)


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
    """Reset de senha pelo admin (não exige senha atual)."""
    new_password: str = Field(alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v):
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Troca da própria senha pelo usuário logado (exige senha atual)."""
    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v):
        return validate_password_strength(v)
