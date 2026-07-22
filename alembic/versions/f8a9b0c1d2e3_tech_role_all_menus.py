"""tech role sees all menus

O perfil Tech (oculto na UI, atribuído manualmente) passa a ter TODOS os grupos
de menu — portanto vê todas as abas da plataforma.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-22

"""
from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # garante o role Tech
    op.execute(
        """
        INSERT INTO roles (name)
        SELECT 'Tech'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'Tech');
        """
    )
    # liga Tech a TODOS os grupos de menu existentes
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'Tech'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    # remove apenas os grupos que não faziam parte do conjunto original do Tech
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'Tech')
          AND menu_group_id IN (
              SELECT id FROM menu_groups
              WHERE code IN ('analytics', 'auditoria', 'producer', 'seller')
          );
        """
    )
