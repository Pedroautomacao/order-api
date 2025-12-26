from pydantic import BaseModel, EmailStr


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

    class Config:
        from_attributes = True
