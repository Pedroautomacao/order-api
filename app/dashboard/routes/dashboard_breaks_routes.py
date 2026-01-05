from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_breaks_schema import (
    DashboardBreaksResponse,
)
from app.dashboard.services.dashboard_breaks_service import (
    DashboardBreaksService,
)

router = APIRouter()


@router.get(
    "/breaks",
    response_model=DashboardBreaksResponse,
    dependencies=[Depends(require_permission("audit:read"))],
)
def dashboard_breaks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardBreaksService.get(db)
