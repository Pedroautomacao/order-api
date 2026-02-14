from sqlalchemy import Column, ForeignKey, Table

from app.database.base import Base

# Nota: menu_group_permissions e role_menu_groups referenciam menu_groups;
# o modelo MenuGroup deve ser importado (em database.imports) para a tabela existir.

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)

menu_group_permissions = Table(
    "menu_group_permissions",
    Base.metadata,
    Column("menu_group_id", ForeignKey("menu_groups.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)

role_menu_groups = Table(
    "role_menu_groups",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("menu_group_id", ForeignKey("menu_groups.id"), primary_key=True),
)