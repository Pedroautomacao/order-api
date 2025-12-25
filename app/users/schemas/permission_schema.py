from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: int
    code: str
    description: str | None

    class Config:
        from_attributes = True
