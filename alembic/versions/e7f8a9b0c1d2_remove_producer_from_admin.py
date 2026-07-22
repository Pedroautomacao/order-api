"""remove producer menu group from Admin role

A tela de Produção deve ficar apenas para o perfil Produtor. O Admin não deve
mais ver/acessar Produção.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-22

"""
from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'Admin')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'producer');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'Admin' AND mg.code = 'producer'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
        """
    )
