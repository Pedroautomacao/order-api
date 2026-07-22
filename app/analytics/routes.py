from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.analytics.service import AnalyticsService
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.get(
    "/overview",
    dependencies=[Depends(require_permission("analytics:read"))],
)
def analytics_overview(
    date_from: date = Query(..., description="Início do range (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fim do range (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Data inicial maior que a final.")
    return AnalyticsService.overview(db, start=date_from, end=date_to)


@router.get(
    "/by-client",
    dependencies=[Depends(require_permission("analytics:read"))],
)
def analytics_by_client(
    client_id: int = Query(..., description="ID do cliente"),
    date_from: date = Query(..., description="Início do range (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fim do range (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Data inicial maior que a final.")
    return AnalyticsService.by_client(db, client_id=client_id, start=date_from, end=date_to)
