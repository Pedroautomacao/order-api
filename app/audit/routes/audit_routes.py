from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.audit.labels import action_label, entity_label
from app.audit.schemas.audit_schema import (
    AuditFilterOption,
    AuditFiltersOptions,
    AuditLogResponse,
)
from app.audit.services.audit_service import AuditService
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


def _parse_date(value: str | None):
    if not value or not value.strip():
        return None
    try:
        # Aceita YYYY-MM-DD ou ISO com hora
        s = value.strip()
        if len(s) == 10:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.replace(tzinfo=ZoneInfo("UTC"))
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@router.get(
    "/logs",
    response_model=list[AuditLogResponse],
    dependencies=[Depends(require_permission("audit:read"))],
)
def list_audit_logs(
    db: Session = Depends(get_db),
    action: str | None = Query(None, description="Filtrar por ação (ex: user:create)"),
    entity: str | None = Query(None, description="Filtrar por entidade (ex: order, user)"),
    user_id: int | None = Query(None, description="Filtrar por ID do usuário"),
    date_from: str | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Data final (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    date_from_dt = _parse_date(date_from)
    date_to_dt = _parse_date(date_to)
    if date_to_dt and date_to_dt.hour == 0 and date_to_dt.minute == 0:
        date_to_dt = date_to_dt + timedelta(days=1)
    return AuditService.list(
        db,
        action=action,
        entity=entity,
        user_id=user_id,
        date_from=date_from_dt,
        date_to=date_to_dt,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/options",
    response_model=AuditFiltersOptions,
    dependencies=[Depends(require_permission("audit:read"))],
)
def get_audit_filter_options(db: Session = Depends(get_db)):
    """Opções dos filtros já rotuladas e ordenadas pelo texto em português."""
    actions, entities = AuditService.get_filter_options(db)

    def opcoes(valores, rotulo):
        return sorted(
            (AuditFilterOption(value=v, label=rotulo(v)) for v in valores),
            key=lambda o: o.label.lower(),
        )

    return AuditFiltersOptions(
        actions=opcoes(actions, action_label),
        entities=opcoes(entities, entity_label),
    )
