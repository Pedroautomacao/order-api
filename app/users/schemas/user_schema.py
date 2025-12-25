from pydantic import BaseModel


class UserBase(BaseModel):
    email: str


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
