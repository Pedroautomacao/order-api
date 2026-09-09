from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.clients.models.client import Client
from app.core.utils.search import normalize_search_string, unaccent_like_sql
from app.clients.schemas.client_schema import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientCreditResponse,
)
from app.clients.services.client_service import ClientService
from app.clients.exception_handler import ClientNotFoundException
from app.orders.services.credit_service import CreditService
from app.users.dependencies.permission_dependencies import require_permission, require_any_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.get(
    "/{client_id}/credit",
    response_model=ClientCreditResponse,
    dependencies=[Depends(require_any_permission("client:read", "order:create"))],
)
def get_client_credit(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Situação de crédito do cliente: limite, em aberto (a prazo não pago) e disponível."""
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.is_deleted.is_(False))
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    outstanding = CreditService.outstanding_credit(db, client_id)
    limit = client.credit_limit or 0
    return ClientCreditResponse(
        client_id=client.id,
        credit_limit=limit,
        outstanding=outstanding,
        available=limit - outstanding,
        allow_cash=client.allow_cash,
        allow_credit=client.allow_credit,
    )


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("client:create"))],
)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ClientService.create(
        db=db,
        data=data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[ClientResponse],
    dependencies=[Depends(require_any_permission("client:read", "order:create"))],
)
def list_clients(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="ID, nome ou CPF/CNPJ do cliente"),
    is_active: bool | None = Query(None, description="Filtrar por ativo (true/false); omitir = todos"),
):
    q = db.query(Client).filter(Client.is_deleted.is_(False))
    if is_active is not None:
        q = q.filter(Client.is_active.is_(is_active))
    if search and search.strip():
        normalized = normalize_search_string(search)
        pattern = f"%{normalized}%"
        conditions = []
        if search.strip().isdigit():
            conditions.append(Client.id == int(search.strip()))
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
        q = q.filter(or_(*conditions))
    return q.order_by(Client.name).all()


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    dependencies=[Depends(require_permission("client:read"))],
)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = (
        db.query(Client)
        .filter(
            Client.id == client_id,
            Client.is_deleted.is_(False),
        )
        .first()
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
    dependencies=[Depends(require_permission("client:update"))],
)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client = (
        db.query(Client)
        .filter(
            Client.id == client_id,
            Client.is_deleted.is_(False),
        )
        .first()
    )

    if not client:
        raise ClientNotFoundException(client_id)

    return ClientService.update(
        db=db,
        client=client,
        data=data,
        current_user=current_user,
    )


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("client:delete"))],
)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client = (
        db.query(Client)
        .filter(
            Client.id == client_id,
            Client.is_deleted.is_(False),
        )
        .first()
    )

    if not client:
        raise ClientNotFoundException(client_id)

    ClientService.delete(
        db=db,
        client=client,
        current_user=current_user,
    )
