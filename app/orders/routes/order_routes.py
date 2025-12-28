from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.clients.exception_handler import ClientNotFoundException
from app.database.deps import get_db
from app.orders.dependencies import get_order_or_404
from app.orders.exception_handler import DuplicateProductInOrderException, InvalidScheduledDateException, \
    DuplicateOrderForClientException, NoOrderAvailableException
from app.orders.models.order import Order
from app.orders.schemas.order_schema import OrderCreate, OrderResponse
from app.orders.serializers.order_serializer import serialize_order
from app.orders.services.order_cancel_service import OrderCancelService
from app.orders.services.order_finish_service import OrderFinishService
from app.orders.services.order_reset_service import OrderResetService
from app.orders.services.order_service import OrderService
from app.products.exception_handler import ProductNotFoundException
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("order:create"))],
)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return OrderService.create(
            db=db,
            data=data,
            current_user=current_user,
        )
    except (ClientNotFoundException, ProductNotFoundException) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, DuplicateProductInOrderException, InvalidScheduledDateException,
            DuplicateOrderForClientException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/assign-next",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:read"))],
)
def assign_next_order(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        order = OrderService.assign_next_order(
            db=db,
            current_user=current_user,
        )
        return serialize_order(order)
    except NoOrderAvailableException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{order_id}/finish",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:read"))],
)
def finish_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = get_order_or_404(db, order_id)
    order = OrderFinishService.finish_order(
        db=db,
        order=order,
        current_user=current_user,
    )
    return serialize_order(order)


@router.patch(
    "/{order_id}/reset",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:reset_production"))],
)
def reset_order(
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

    return OrderResetService.reset(
        db=db,
        order=order,
        current_user=current_user,
    )


@router.patch(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:cancel"))],
)
def cancel_order(
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

    is_admin = current_user.role.name == "admin"

    return OrderCancelService.cancel(
        db=db,
        order=order,
        current_user=current_user,
        is_admin=is_admin,
    )



