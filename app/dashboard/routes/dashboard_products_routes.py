from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

from app.dashboard.schemas.dashboard_products_schema import (
    DashboardProductsResponse,
)
from app.dashboard.services.dashboard_products_service import (
    DashboardProductsService,
)

router = APIRouter()


@router.get(
    "/dashboard/products",
    response_model=DashboardProductsResponse,
    dependencies=[require_permission("audit:read")],
)
def dashboard_products(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardProductsService.get(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )
