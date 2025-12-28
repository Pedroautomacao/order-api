from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dashboard.schemas.dashboard_user_schema import DashboardUsersResponse
from app.dashboard.services.dashboard_user_service import DashboardUsersService
from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.get(
    "/users",
    response_model=DashboardUsersResponse,
    dependencies=[require_permission("audit:read")],
)
def dashboard_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardUsersService.get(db)
