from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.orders.schemas.order_item_schema import OrderItemConfirm
from app.orders.schemas.order_schema import OrderResponse
from app.orders.serializers.order_serializer import serialize_order
from app.orders.services.order_item_service import OrderItemService
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.patch(
    "/{order_item_id}/confirm",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:read"))],
)
def confirm_order_item(
    order_item_id: int,
    data: OrderItemConfirm,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = OrderItemService.confirm_item(
        db=db,
        order_item_id=order_item_id,
        data=data,
        current_user=current_user,
    )

    return serialize_order(order)

