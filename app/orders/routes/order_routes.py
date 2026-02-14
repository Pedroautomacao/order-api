from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session, joinedload

from app.clients.exception_handler import ClientNotFoundException
from app.clients.models.client import Client
from app.core.utils.search import normalize_search_string, unaccent_like_sql
from app.database.deps import get_db
from app.orders.dependencies import get_order_or_404
from app.orders.exception_handler import DuplicateProductInOrderException, InvalidScheduledDateException, \
    DuplicateOrderForClientException, NoOrderAvailableException
from app.orders.models.order import Order
from app.orders.enums import OrderStatus
from app.orders.schemas.order_schema import OrderCreate, OrderResponse, OrderListResponse
from app.orders.serializers.order_serializer import serialize_order, serialize_order_list_item
from app.orders.services.order_cancel_service import OrderCancelService
from app.orders.services.order_finish_service import OrderFinishService
from app.orders.services.order_reset_service import OrderResetService
from app.orders.services.order_service import OrderService
from app.products.exception_handler import ProductNotFoundException
from app.users.dependencies.auth_dependencies import get_current_user
from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.get(
    "/",
    response_model=list[OrderListResponse],
    dependencies=[Depends(require_permission("order:read"))],
)
def list_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: str | None = Query(None, description="ID do pedido, nome ou CNPJ do cliente"),
    status: str | None = Query(None, description="Filtrar por status do pedido"),
):
    q = (
        db.query(Order)
        .filter(Order.is_deleted.is_(False))
        .options(joinedload(Order.client))
    )
    if status and status.strip():
        try:
            status_enum = OrderStatus(status.strip())
            q = q.filter(Order.status == status_enum)
        except ValueError:
            pass
    if search and search.strip():
        normalized = normalize_search_string(search)
        pattern = f"%{normalized}%"
        conditions = []
        if search.strip().isdigit():
            conditions.append(Order.id == int(search.strip()))
        use_unaccent = db.get_bind().dialect.name == "postgresql"
        if use_unaccent:
            conditions.append(
                text(unaccent_like_sql([("clients", "name"), ("clients", "cpf_cnpj")])).bindparams(
                    search_pattern=pattern
                )
            )
        else:
            conditions.append(func.lower(Client.name).like(pattern))
            conditions.append(func.lower(Client.cpf_cnpj).like(pattern))
        q = q.join(Order.client).filter(or_(*conditions))
    q = q.order_by(Order.scheduled_date.desc(), Order.id.desc())
    orders = q.all()
    return [serialize_order_list_item(o) for o in orders]


@router.get(
    "/fiscal",
    response_model=list[OrderListResponse],
    dependencies=[Depends(require_permission("order:bill"))],
)
def list_fiscal_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: str | None = Query(None, description="ID do pedido, nome ou CNPJ do cliente"),
    status: str | None = Query(None, description="Filtrar por status (Produced, Billed)"),
):
    """Lista pedidos visíveis ao fiscal (Produced, Billed). Requer order:bill."""
    FISCAL_STATUSES = (OrderStatus.PRODUCED, OrderStatus.BILLED)
    q = (
        db.query(Order)
        .filter(Order.is_deleted.is_(False))
        .filter(Order.status.in_(FISCAL_STATUSES))
        .options(joinedload(Order.client))
    )
    if status and status.strip():
        try:
            status_enum = OrderStatus(status.strip())
            if status_enum in FISCAL_STATUSES:
                q = q.filter(Order.status == status_enum)
        except ValueError:
            pass
    if search and search.strip():
        normalized = normalize_search_string(search)
        pattern = f"%{normalized}%"
        conditions = []
        if search.strip().isdigit():
            conditions.append(Order.id == int(search.strip()))
        use_unaccent = db.get_bind().dialect.name == "postgresql"
        if use_unaccent:
            conditions.append(
                text(unaccent_like_sql([("clients", "name"), ("clients", "cpf_cnpj")])).bindparams(
                    search_pattern=pattern
                )
            )
        else:
            conditions.append(func.lower(Client.name).like(pattern))
            conditions.append(func.lower(Client.cpf_cnpj).like(pattern))
        q = q.join(Order.client).filter(or_(*conditions))
    q = q.order_by(Order.scheduled_date.desc(), Order.id.desc())
    orders = q.all()
    return [serialize_order_list_item(o) for o in orders]


@router.get(
    "/fiscal/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:bill"))],
)
def get_fiscal_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Detalhe do pedido para fiscal. Só retorna se status for Produced ou Billed."""
    order = get_order_or_404(db, order_id)
    if order.status not in (OrderStatus.PRODUCED, OrderStatus.BILLED):
        raise HTTPException(status_code=404, detail="Pedido não disponível para fiscal")
    return serialize_order(order)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:read"))],
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = get_order_or_404(db, order_id)
    return serialize_order(order)


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



