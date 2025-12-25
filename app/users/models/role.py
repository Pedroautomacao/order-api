from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.associations import user_roles, role_permissions

if TYPE_CHECKING:
    from app.users.models.user import User
    from app.users.models.permission import Permission


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )
