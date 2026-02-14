"""add menu_groups for admin menu (one group per menu item)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: menu groups so users can have a combination of menus

"""
from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "menu_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "menu_group_permissions",
        sa.Column("menu_group_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["menu_group_id"], ["menu_groups.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.PrimaryKeyConstraint("menu_group_id", "permission_id"),
    )

    op.create_table(
        "role_menu_groups",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("menu_group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["menu_group_id"], ["menu_groups.id"]),
        sa.PrimaryKeyConstraint("role_id", "menu_group_id"),
    )

    # Um grupo por item do menu admin
    op.execute(
        """
        INSERT INTO menu_groups (code, name, description)
        VALUES
            ('dashboard', 'Dashboard', 'Menu Dashboard'),
            ('orders', 'Pedidos', 'Menu Pedidos'),
            ('fiscal', 'Fiscal', 'Menu Fiscal'),
            ('products', 'Produtos', 'Menu Produtos'),
            ('clients', 'Clientes', 'Menu Clientes'),
            ('users', 'Usuários', 'Menu Usuários')
        ;
        """
    )

    # Cada grupo dá a permissão correspondente ao menu
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg
        JOIN permissions p ON (
            (mg.code = 'dashboard' AND p.code = 'dashboard:read')
            OR (mg.code = 'orders' AND p.code = 'order:read')
            OR (mg.code = 'fiscal' AND p.code = 'order:bill')
            OR (mg.code = 'products' AND p.code = 'product:read')
            OR (mg.code = 'clients' AND p.code = 'client:read')
            OR (mg.code = 'users' AND p.code = 'user:create')
        )
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )

    # Admin: todos os grupos. Fiscal: só grupo fiscal.
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r
        CROSS JOIN menu_groups mg
        WHERE r.name = 'admin'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r
        JOIN menu_groups mg ON mg.code = 'fiscal'
        WHERE r.name = 'fiscal'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("role_menu_groups")
    op.drop_table("menu_group_permissions")
    op.drop_table("menu_groups")
