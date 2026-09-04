from sqlalchemy.orm import Session

from app.units.models.unit_of_measure import UnitOfMeasure
from app.units.schemas.unit_schema import UnitCreate, UnitUpdate
from app.units.exception_handler import UnitNotFoundException
from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.users.models.user import User


class UnitService:
    @staticmethod
    def create(
        db: Session,
        *,
        data: UnitCreate,
        current_user: User,
    ) -> UnitOfMeasure:
        unit = UnitOfMeasure(
            code=data.code.lower(),
            name=data.name,
            description=data.description,
            is_active=data.is_active,
        )

        with atomic(db):
            db.add(unit)
            db.flush()  # precisa do id gerado para o log

            AuditService.log(
                db=db,
                action="unit:create",
                entity="unit_of_measure",
                entity_id=unit.id,
                user_id=current_user.id,
                description=f"Unit {unit.code} created by {current_user.username}",
            )

        db.refresh(unit)
        return unit

    @staticmethod
    def update(
        db: Session,
        *,
        unit: UnitOfMeasure,
        data: UnitUpdate,
        current_user: User,
    ) -> UnitOfMeasure:
        with atomic(db):
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(unit, field, value)

            AuditService.log(
                db=db,
                action="unit:update",
                entity="unit_of_measure",
                entity_id=unit.id,
                user_id=current_user.id,
                description=f"Unit {unit.code} updated by {current_user.username}",
            )

        db.refresh(unit)
        return unit

    @staticmethod
    def delete(
        db: Session,
        *,
        unit: UnitOfMeasure,
        current_user: User,
    ) -> None:
        if unit.is_deleted:
            return

        with atomic(db):
            unit.is_deleted = True

            AuditService.log(
                db=db,
                action="unit:delete",
                entity="unit_of_measure",
                entity_id=unit.id,
                user_id=current_user.id,
                description=f"Unit {unit.code} deleted by {current_user.username}",
            )
