from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.clients.schemas.client_schema import ClientCreate, ClientUpdate
from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.users.models import User


class ClientService:
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
        with atomic(db):
            db.add(client)
            db.flush()  # precisa do id gerado para o log

            AuditService.log(
                db=db,
                action="client:create",
                entity="client",
                entity_id=client.id,
                user_id=current_user.id,
                description=f"Cliente {client.name} cadastrado",
            )

        db.refresh(client)
        return client

    @staticmethod
    def update(
        db: Session,
        *,
        client: Client,
        data: ClientUpdate,
        current_user: User,
    ) -> Client:
        with atomic(db):
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(client, field, value)

            AuditService.log(
                db=db,
                action="client:update",
                entity="client",
                entity_id=client.id,
                user_id=current_user.id,
                description=f"Cliente {client.name} atualizado",
            )

        db.refresh(client)
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

        with atomic(db):
            client.is_deleted = True

            AuditService.log(
                db=db,
                action="client:delete",
                entity="client",
                entity_id=client.id,
                user_id=current_user.id,
                description=f"Cliente {client.name} excluído",
            )
