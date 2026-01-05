from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dashboard.services.dashboard_overview_service import DashboardService
from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_overview_schema import DashboardOverviewResponse

router = APIRouter()


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    dependencies=[Depends(require_permission("audit:read"))],
)
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardService.overview(db)
