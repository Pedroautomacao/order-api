from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_billing_schema import (
    DashboardBillingResponse,
)
from app.dashboard.services.dashboard_billing_service import (
    DashboardBillingService,
)

router = APIRouter()


@router.get(
    "/billing",
    response_model=DashboardBillingResponse,
    dependencies=[Depends(require_permission("audit:read"))],
)
def dashboard_billing(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardBillingService.get(db)
