from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_production_schema import (
    DashboardProductionResponse,
)
from app.dashboard.services.dashboard_production_service import (
    DashboardProductionService,
)

router = APIRouter()


@router.get(
    "/production",
    response_model=DashboardProductionResponse,
    dependencies=[require_permission("audit:read")],
)
def dashboard_production(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardProductionService.get(db)
