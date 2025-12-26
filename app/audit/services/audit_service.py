from collections.abc import Sequence
from datetime import datetime
from sqlalchemy.orm import Session

from app.audit.models.audit_log import AuditLog
from app.core.services.base_atomic_service import BaseAtomicService


class AuditService(BaseAtomicService):
    @staticmethod
    def list(
        db: Session,
        *,
        action: str | None = None,
        entity: str | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        query = db.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action)

        if entity:
            query = query.filter(AuditLog.entity == entity)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if date_from:
            query = query.filter(AuditLog.created_at >= date_from)

        if date_to:
            query = query.filter(AuditLog.created_at <= date_to)

        return (
            query
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def log(
        db: Session,
        *,
        action: str,
        entity: str,
        entity_id: int | None,
        user_id: int | None,
        description: str | None = None,
    ) -> None:
        log = AuditLog(
            action=action,
            entity=entity,
            entity_id=entity_id,
            user_id=user_id,
            description=description,
        )
        db.add(log)
        db.commit()