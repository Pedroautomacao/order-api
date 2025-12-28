from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_producers_schema import (
    DashboardProducersResponse,
)
from app.dashboard.services.dashboard_producers_service import (
    DashboardProducersService,
)

router = APIRouter()


@router.get(
    "/producers",
    response_model=DashboardProducersResponse,
    dependencies=[require_permission("audit:read")],
)
def dashboard_producers(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardProducersService.get(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )
