from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dashboard.snapshot.models.dashboard_snapshot import DashboardSnapshot
from app.database.deps import get_db
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.get(
    "/latest",
    dependencies=[require_permission("audit:read")],
)
def get_latest_dashboard_snapshot(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    snapshot = (
        db.query(DashboardSnapshot)
        .order_by(DashboardSnapshot.generated_at.desc())
        .first()
    )

    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="Dashboard snapshot not found",
        )

    return snapshot.payload
