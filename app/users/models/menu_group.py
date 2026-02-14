from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.associations import menu_group_permissions, role_menu_groups

if TYPE_CHECKING:
    from app.users.models.permission import Permission
    from app.users.models.role import Role


class MenuGroup(Base):
    """Grupo de menu do admin. Cada grupo corresponde a um item do menu (Dashboard, Pedidos, Fiscal, etc.)."""

    __tablename__ = "menu_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=menu_group_permissions,
        back_populates="menu_groups",
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_menu_groups,
        back_populates="menu_groups",
    )
