from datetime import datetime
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity: str
    entity_id: int | None
    description: str | None
    user_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True
