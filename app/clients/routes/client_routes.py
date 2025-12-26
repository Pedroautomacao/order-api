from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.clients.models.client import Client
from app.clients.schemas.client_schema import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
)
from app.clients.services.client_service import ClientService
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.post(
    "/",
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
    "/",
    response_model=list[ClientResponse],
    dependencies=[Depends(require_permission("client:create"))],
)
def list_clients(db: Session = Depends(get_db)):
    return (
        db.query(Client)
        .filter(Client.is_deleted.is_(False))
        .order_by(Client.name)
        .all()
    )


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    dependencies=[Depends(require_permission("client:create"))],
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
        raise HTTPException(status_code=404, detail="Client not found")

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
        raise HTTPException(status_code=404, detail="Client not found")

    ClientService.delete(
        db=db,
        client=client,
        current_user=current_user,
    )
