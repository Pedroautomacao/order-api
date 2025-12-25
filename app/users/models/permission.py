from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.associations import role_permissions

if TYPE_CHECKING:
    from app.users.models.role import Role


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )
