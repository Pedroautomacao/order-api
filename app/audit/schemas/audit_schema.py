from datetime import datetime
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity: str
    entity_id: int | None
    description: str | None
    user_id: int | None
    username: str | None = None
    created_at: datetime

    # Rótulos em português. A chave crua continua em action/entity porque é
    # o que os filtros usam.
    action_label: str
    entity_label: str

    class Config:
        from_attributes = True


class AuditFilterOption(BaseModel):
    """Opção de filtro: `value` filtra, `label` aparece na tela."""

    value: str
    label: str


class AuditFiltersOptions(BaseModel):
    actions: list[AuditFilterOption]
    entities: list[AuditFilterOption]
