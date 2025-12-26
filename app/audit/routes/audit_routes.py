from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.audit.schemas.audit_schema import AuditLogResponse
from app.audit.services.audit_service import AuditService
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.get(
    "/logs",
    response_model=list[AuditLogResponse],
    dependencies=[Depends(require_permission("audit:read"))],
)
def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return AuditService.list(db, limit=limit, offset=offset)
