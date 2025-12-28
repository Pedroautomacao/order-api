from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

from app.orders.models.order import Order
from app.orders.schemas.order_schema import OrderResponse
from app.billing.services.billing_service import BillingService

router = APIRouter()


@router.patch(
    "/{order_id}/bill",
    response_model=OrderResponse,
    dependencies=[require_permission("order:bill")],
)
def bill_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.is_deleted.is_(False),
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return BillingService.bill(
        db=db,
        order=order,
        current_user=current_user,
    )
