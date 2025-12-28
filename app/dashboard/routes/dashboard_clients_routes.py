from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_clients_schema import (
    DashboardClientsResponse,
)
from app.dashboard.services.dashboard_clients_service import (
    DashboardClientsService,
)

router = APIRouter()


@router.get(
    "/clients",
    response_model=DashboardClientsResponse,
    dependencies=[require_permission("audit:read")],
)
def dashboard_clients(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardClientsService.get(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )
