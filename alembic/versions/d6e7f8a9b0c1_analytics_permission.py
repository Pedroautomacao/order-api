"""analytics permission and menu group

- permission analytics:read
- menu group 'analytics' (para aparecer no controle de grupos de menu)
- vincula a permissão ao grupo e o grupo ao perfil Admin

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-22

"""
from alembic import op

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # permissão
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('analytics:read', 'Ver relatórios (analytics)')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    # grupo de menu
    op.execute(
        """
        INSERT INTO menu_groups (code, name, description)
        VALUES ('analytics', 'Relatórios', 'Relatórios e análises de pedidos')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    # permissão -> grupo
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'analytics' AND p.code = 'analytics:read'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )
    # grupo -> perfil Admin
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'Admin' AND mg.code = 'analytics'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE menu_group_id IN (SELECT id FROM menu_groups WHERE code = 'analytics');
        """
    )
    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE menu_group_id IN (SELECT id FROM menu_groups WHERE code = 'analytics');
        """
    )
    op.execute("DELETE FROM menu_groups WHERE code = 'analytics';")
    op.execute("DELETE FROM permissions WHERE code = 'analytics:read';")
