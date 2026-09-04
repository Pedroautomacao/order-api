from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import AuditMixin


class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    cpf: Mapped[str] = mapped_column(
        String(14),
        nullable=False,
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
    )

    @property
    def full_name(self) -> str:
        """Nome de exibição. Cai no username quando não houver nome."""
        nome = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return nome or self.username
