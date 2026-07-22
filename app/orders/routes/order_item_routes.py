from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.orders.exception_handler import (
    OrderNotAssignedToUserException,
    InvalidOrderItemStateException,
    InvalidProducedQuantityException,
    WorkItemNotFoundException,
)
from app.orders.schemas.order_item_schema import OrderItemConfirm
from app.orders.schemas.order_schema import OrderResponse
from app.orders.serializers.order_serializer import serialize_order
from app.orders.services.order_item_service import OrderItemService
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


def _handle_item_errors(fn):
    try:
        return fn()
    except OrderNotAssignedToUserException:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    except InvalidOrderItemStateException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (InvalidProducedQuantityException, WorkItemNotFoundException, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{order_item_id}/confirm",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:produce"))],
)
def confirm_order_item(
    order_item_id: int,
    data: OrderItemConfirm,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = _handle_item_errors(
        lambda: OrderItemService.confirm_item(
            db=db,
            order_item_id=order_item_id,
            data=data,
            current_user=current_user,
        )
    )
    return serialize_order(order)


@router.patch(
    "/{order_item_id}/update-quantity",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:produce"))],
)
def update_item_quantity(
    order_item_id: int,
    data: OrderItemConfirm,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Atualiza a quantidade produzida de um item já confirmado (PRODUCED)."""
    order = _handle_item_errors(
        lambda: OrderItemService.update_produced_quantity(
            db=db,
            order_item_id=order_item_id,
            data=data,
            current_user=current_user,
        )
    )
    return serialize_order(order)

