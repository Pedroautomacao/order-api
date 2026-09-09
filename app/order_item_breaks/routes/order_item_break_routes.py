from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.order_item_breaks.schemas.order_item_break_schema import OrderItemBreakResponse
from app.order_item_breaks.services.order_item_break_service import (
    OrderItemBreakService,
)
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.get(
    "",
    response_model=list[OrderItemBreakResponse],
    dependencies=[Depends(require_permission("order_item_break:read"))],
)
def list_order_item_breaks(
    order_id: UUID | None = None,
    order_item_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return OrderItemBreakService.list(
        db,
        order_id=order_id,
        order_item_id=order_item_id,
    )
