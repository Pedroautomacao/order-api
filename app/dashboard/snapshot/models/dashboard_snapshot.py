from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON, DateTime
from datetime import datetime

from app.database.base import Base
from app.database.mixins import AuditMixin


class DashboardSnapshot(Base, AuditMixin):
    __tablename__ = "dashboard_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Snapshot completo do dashboard",
    )
