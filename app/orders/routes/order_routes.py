from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.clients.exception_handler import ClientNotFoundException
from app.clients.models.client import Client
from app.core.utils.search import normalize_search_string, unaccent_like_sql
from app.database.deps import get_db
from app.orders.dependencies import get_order_or_404, with_detail_relations
from app.orders.exception_handler import DuplicateProductInOrderException, InvalidScheduledDateException, \
    DuplicateOrderForClientException, NoOrderAvailableException, CreditLimitExceededException, \
    PaymentMethodNotAllowedException
from app.orders.services.order_payment_service import OrderPaymentService
from app.orders.services.order_admin_service import OrderAdminService
from app.orders.services.order_production_approval_service import (
    OrderProductionApprovalService,
)
from pydantic import BaseModel, Field as PydField


class RescheduleRequest(BaseModel):
    scheduled_date: date = PydField(alias="scheduledDate")

    class Config:
        populate_by_name = True
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.products.models.product import Product
from app.orders.enums import OrderStatus, ProductionApproval
from app.core.time import today_sp
from app.core.schemas.pagination import Page
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


def _apply_order_filters(
    q,
    *,
    db: Session,
    search: str | None,
    status: str | None,
    scheduled_date: date | None,
    production_approval: str | None = None,
):
    """Filtros de listagem de pedido, compartilhados pelas três telas.

    Status desconhecido é ignorado em vez de virar erro, mantendo o
    comportamento que as telas já esperam — vale também para a liberação
    de produção.
    """
    if scheduled_date:
        q = q.filter(Order.scheduled_date == scheduled_date)

    if production_approval and production_approval.strip():
        try:
            q = q.filter(
                Order.production_approval
                == ProductionApproval(production_approval.strip())
            )
        except ValueError:
            pass

    if status and status.strip():
        try:
            q = q.filter(Order.status == OrderStatus(status.strip()))
        except ValueError:
            pass

    if search and search.strip():
        normalized = normalize_search_string(search)
        pattern = f"%{normalized}%"
        conditions = []
        if search.strip().isdigit():
            conditions.append(Order.id == int(search.strip()))
        if db.get_bind().dialect.name == "postgresql":
            conditions.append(
                text(
                    unaccent_like_sql([("clients", "name"), ("clients", "cpf_cnpj")])
                ).bindparams(search_pattern=pattern)
            )
        else:
            conditions.append(func.lower(Client.name).like(pattern))
            conditions.append(func.lower(Client.cpf_cnpj).like(pattern))
        q = q.join(Order.client).filter(or_(*conditions))

    return q


@router.get(
    "",
    response_model=Page[OrderListResponse],
    dependencies=[Depends(require_permission("order:read"))],
)
def list_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: str | None = Query(None, description="ID do pedido, nome ou CNPJ do cliente"),
    status: str | None = Query(None, description="Filtrar por status do pedido"),
    production_approval: str | None = Query(
        None,
        alias="productionApproval",
        description="Filtrar por liberação de produção (Awaiting, Approved, Recused)",
    ),
    scheduled_date: date | None = Query(None, description="Filtrar por data de entrega (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Página, começando em 1"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
):
    """Todos os pedidos, dos mais recentes para os mais antigos por data de entrega.

    A paginação é feita no banco: sem ela a tela precisaria baixar a base inteira
    para paginar no cliente.
    """
    base = _apply_order_filters(
        db.query(Order).filter(Order.is_deleted.is_(False)),
        db=db,
        search=search,
        status=status,
        scheduled_date=scheduled_date,
        production_approval=production_approval,
    )

    total = base.with_entities(func.count(Order.id)).order_by(None).scalar() or 0

    orders = (
        # selectinload em vez de joinedload: com `search` o filtro já fez INNER
        # JOIN em clients, e o joinedload adicionava um segundo LEFT OUTER JOIN
        # aliasado da mesma tabela só para carregar o relacionamento
        base.options(selectinload(Order.client))
        .order_by(Order.scheduled_date.desc(), Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return Page[OrderListResponse].build(
        [serialize_order_list_item(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    # o status pedido só vale se estiver dentro do recorte do fiscal
    fiscal_status = None
    if status and status.strip():
        try:
            if OrderStatus(status.strip()) in FISCAL_STATUSES:
                fiscal_status = status
        except ValueError:
            pass
    q = _apply_order_filters(
        q,
        db=db,
        search=search,
        status=fiscal_status,
        scheduled_date=scheduled_date,
    )
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
            _jl(Order.created_by),
            _jl(Order.items).joinedload(OrderItem.product).joinedload(Product.unit_of_measure),
        )
        .order_by(Order.id.asc())
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
    """Lista apenas os pedidos criados pelo vendedor logado.

    Sem filtro de data, traz de hoje em diante — o que o vendedor ainda pode
    acompanhar — da data mais próxima para a mais distante. Data passada só
    aparece quando ele filtra por ela explicitamente.
    """
    q = (
        db.query(Order)
        .filter(
            Order.is_deleted.is_(False),
            Order.created_by_user_id == current_user.id,
        )
        .options(joinedload(Order.client))
    )
    if not scheduled_date:
        q = q.filter(Order.scheduled_date >= today_sp())

    q = _apply_order_filters(
        q,
        db=db,
        search=search,
        status=status,
        scheduled_date=scheduled_date,
    )
    # crescente: hoje primeiro, depois as datas seguintes em sequência
    q = q.order_by(Order.scheduled_date.asc(), Order.id.desc())
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
    "",
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
        with_detail_relations(db.query(Order))
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
        with_detail_relations(db.query(Order))
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


@router.patch(
    "/{order_id}/prioritize",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:set_priority"))],
)
def prioritize_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Prioriza o pedido (prioridade = 'A')."""
    order = get_order_or_404(db, order_id)
    return serialize_order(
        OrderAdminService.prioritize(db=db, order=order, current_user=current_user)
    )


@router.patch(
    "/{order_id}/approve-production",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:approve_production"))],
)
def approve_order_production(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Libera o pedido para entrar na fila de produção."""
    order = get_order_or_404(db, order_id)
    return serialize_order(
        OrderProductionApprovalService.approve(
            db=db, order=order, current_user=current_user
        )
    )


@router.patch(
    "/{order_id}/recuse-production",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:approve_production"))],
)
def recuse_order_production(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Barra o pedido: ele sai da fila de produção."""
    order = get_order_or_404(db, order_id)
    return serialize_order(
        OrderProductionApprovalService.recuse(
            db=db, order=order, current_user=current_user
        )
    )


@router.patch(
    "/{order_id}/reschedule",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:read"))],
)
def reschedule_order(
    order_id: int,
    data: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remarca a data de entrega (só pedidos em Aguardando)."""
    order = get_order_or_404(db, order_id)
    return serialize_order(
        OrderAdminService.reschedule(
            db=db, order=order, new_date=data.scheduled_date, current_user=current_user
        )
    )



