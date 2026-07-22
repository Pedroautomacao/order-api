from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.clients.schemas.client_schema import ClientCreate, ClientUpdate
from app.audit.services.audit_service import AuditService
from app.core.services.base_atomic_service import BaseAtomicService
from app.users.models import User


class ClientService(BaseAtomicService):
    @staticmethod
    def create(
        db: Session,
        *,
        data: ClientCreate,
        current_user: User,
    ) -> Client:
        client = Client(
            name=data.name,
            priority=data.priority,
            cpf_cnpj=data.cpf_cnpj,
            address=data.address,
            phone_number=data.phone_number,
            observations=data.observations,
            is_active=data.is_active,
            allow_cash=data.allow_cash,
            allow_credit=data.allow_credit,
            credit_limit=data.credit_limit,
        )
        db.add(client)
        db.commit()
        db.refresh(client)

        AuditService.log(
            db=db,
            action="client:create",
            entity="client",
            entity_id=client.id,
            user_id=current_user.id,
            description=f"Client {client.name} created by {current_user.username}",
        )

        return client

    @staticmethod
    def update(
        db: Session,
        *,
        client: Client,
        data: ClientUpdate,
        current_user: User,
    ) -> Client:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(client, field, value)

        db.commit()
        db.refresh(client)

        AuditService.log(
            db=db,
            action="client:update",
            entity="client",
            entity_id=client.id,
            user_id=current_user.id,
            description=f"Client {client.name} updated by {current_user.username}",
        )

        return client

    @staticmethod
    def delete(
        db: Session,
        *,
        client: Client,
        current_user: User,
    ) -> None:
        if client.is_deleted:
            return

        client.is_deleted = True
        db.commit()

        AuditService.log(
            db=db,
            action="client:delete",
            entity="client",
            entity_id=client.id,
            user_id=current_user.id,
            description=f"Client {client.name} soft deleted by {current_user.username}",
        )
