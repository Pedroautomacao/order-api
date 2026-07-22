from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session, joinedload

from app.clients.exception_handler import ClientNotFoundException
from app.clients.models.client import Client
from app.core.utils.search import normalize_search_string, unaccent_like_sql
from app.database.deps import get_db
from app.orders.dependencies import get_order_or_404
from app.orders.exception_handler import DuplicateProductInOrderException, InvalidScheduledDateException, \
    DuplicateOrderForClientException, NoOrderAvailableException, CreditLimitExceededException, \
    PaymentMethodNotAllowedException
from app.orders.services.order_payment_service import OrderPaymentService
from app.orders.models.order import Order
from app.orders.enums import OrderStatus
from app.orders.schemas.order_schema import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse
from app.orders.serializers.order_serializer import serialize_order, serialize_order_list_item
from app.orders.services.order_cancel_service import OrderCancelService
from app.orders.services.order_finish_service import OrderFinishService
from app.orders.services.order_reset_service import OrderResetService
from app.orders.services.order_service import OrderService
from app.orders.services.order_update_service import OrderUpdateService
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
    scheduled_date: date | None = Query(None, description="Filtrar por data de entrega (YYYY-MM-DD)"),
):
    q = (
        db.query(Order)
        .filter(Order.is_deleted.is_(False))
        .options(joinedload(Order.client))
    )
    if scheduled_date:
        q = q.filter(Order.scheduled_date == scheduled_date)
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
    scheduled_date: date | None = Query(None, description="Filtrar por data de entrega (YYYY-MM-DD)"),
):
    """Lista pedidos visíveis ao fiscal (Produced, Billed). Requer order:bill."""
    FISCAL_STATUSES = (OrderStatus.PRODUCED, OrderStatus.BILLED)
    q = (
        db.query(Order)
        .filter(Order.is_deleted.is_(False))
        .filter(Order.status.in_(FISCAL_STATUSES))
        .options(joinedload(Order.client))
    )
    if scheduled_date:
        q = q.filter(Order.scheduled_date == scheduled_date)
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
    "/producer/current",
    response_model=OrderResponse | None,
    dependencies=[Depends(require_permission("order:produce"))],
)
def get_producer_current_order(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retorna o pedido atualmente em produção pelo produtor logado, ou null."""
    from sqlalchemy.orm import joinedload as _jl
    order = (
        db.query(Order)
        .filter(
            Order.status == OrderStatus.PRODUCING,
            Order.assigned_user_id == current_user.id,
            Order.is_deleted.is_(False),
        )
        .options(
            _jl(Order.client),
            _jl(Order.items),
        )
        .first()
    )
    if not order:
        return None
    return serialize_order(order)


@router.post(
    "/producer/next",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:produce"))],
)
def assign_next_producer_order(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Atribui o próximo pedido Aguardando ao produtor logado."""
    try:
        order = OrderService.assign_next_order(db=db, current_user=current_user)
        return serialize_order(order)
    except NoOrderAvailableException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/producer/{order_id}/finish",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:produce"))],
)
def finish_producer_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Finaliza pedido em produção do produtor logado."""
    order = get_order_or_404(db, order_id)
    if order.assigned_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    order = OrderFinishService.finish_order(db=db, order=order, current_user=current_user)
    return serialize_order(order)


@router.get(
    "/seller",
    response_model=list[OrderListResponse],
    dependencies=[Depends(require_permission("order:list"))],
)
def list_seller_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: str | None = Query(None, description="ID do pedido, nome ou CNPJ do cliente"),
    status: str | None = Query(None, description="Filtrar por status do pedido"),
    scheduled_date: date | None = Query(None, description="Filtrar por data de entrega (YYYY-MM-DD)"),
):
    """Lista apenas os pedidos criados pelo vendedor logado."""
    q = (
        db.query(Order)
        .filter(
            Order.is_deleted.is_(False),
            Order.created_by_user_id == current_user.id,
        )
        .options(joinedload(Order.client))
    )
    if scheduled_date:
        q = q.filter(Order.scheduled_date == scheduled_date)
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
    return [serialize_order_list_item(o) for o in q.all()]


@router.get(
    "/seller/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:list"))],
)
def get_seller_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Detalhe de pedido do vendedor. Só retorna se o pedido foi criado pelo usuário logado."""
    order = get_order_or_404(db, order_id)
    if order.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return serialize_order(order)


@router.put(
    "/seller/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:list"))],
)
def update_seller_order(
    order_id: int,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Edita pedido do vendedor. Só permitido enquanto estiver Aguardando."""
    order = get_order_or_404(db, order_id)
    try:
        order = OrderUpdateService.update(db=db, order=order, data=data, current_user=current_user)
        return serialize_order(order)
    except (ClientNotFoundException, ProductNotFoundException) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, DuplicateProductInOrderException, InvalidScheduledDateException,
            DuplicateOrderForClientException, CreditLimitExceededException,
            PaymentMethodNotAllowedException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/seller/{order_id}/cancel",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:list"))],
)
def cancel_seller_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cancela pedido do vendedor. Só permitido enquanto estiver Aguardando."""
    order = get_order_or_404(db, order_id)
    if order.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if order.status != OrderStatus.AWAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas pedidos em Aguardando podem ser cancelados pelo vendedor.",
        )
    return serialize_order(OrderCancelService.cancel(db=db, order=order, current_user=current_user, is_admin=False))


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
        order = OrderService.create(
            db=db,
            data=data,
            current_user=current_user,
        )
        return serialize_order(order)
    except (ClientNotFoundException, ProductNotFoundException) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, DuplicateProductInOrderException, InvalidScheduledDateException,
            DuplicateOrderForClientException, CreditLimitExceededException,
            PaymentMethodNotAllowedException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch(
    "/{order_id}/pay",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:mark_paid"))],
)
def mark_order_paid(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Marca um pedido como pago (somente admin). Libera o limite de crédito do cliente."""
    order = get_order_or_404(db, order_id)
    return serialize_order(
        OrderPaymentService.mark_paid(db=db, order=order, current_user=current_user)
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

    return serialize_order(OrderResetService.reset(
        db=db,
        order=order,
        current_user=current_user,
    ))


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

    return serialize_order(OrderCancelService.cancel(
        db=db,
        order=order,
        current_user=current_user,
        is_admin=is_admin,
    ))



