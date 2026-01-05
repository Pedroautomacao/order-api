from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.ranking.schemas.rankings_schema import RankingsResponse
from app.ranking.services.rankings_service import RankingsService
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/rankings", tags=["Rankings"])


@router.get(
    "",
    response_model=RankingsResponse,
    dependencies=[Depends(require_permission("audit:read"))],
)
def get_rankings(
    limit: int = 10,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return RankingsService.get(
        db=db,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )
