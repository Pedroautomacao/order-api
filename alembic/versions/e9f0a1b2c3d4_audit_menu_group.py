"""menu group for the audit screen

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-09-10

A permissão audit:read existe desde o seed, mas nunca foi pendurada em nenhum
grupo de menu — só concedida direto aos roles. Como PermissionService ignora as
permissões diretas de um perfil que tenha grupos de menu, ninguém conseguia
abrir /admin/audit: nem admin, nem Tech.

Cria o grupo `audit` para a tela, no mesmo formato do grupo `analytics`, e o
atribui aos perfis administrativos.

O filtro usa lower(r.name) de propósito: as migrations inserem 'admin' e 'tech'
minúsculos, mas também 'Tech', e outras referenciam 'Admin' — que nenhuma
migration cria. Comparar sem diferenciar caixa evita que o grant falhe calado
por causa do ON CONFLICT DO NOTHING.
"""
from alembic import op


revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a permissão já vem do seed; idempotente para instalação que não a tenha
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('audit:read', 'Ver logs de auditoria')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO menu_groups (code, name, description)
        VALUES ('audit', 'Auditoria', 'Menu Auditoria')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'audit' AND p.code = 'audit:read'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE lower(r.name) IN ('admin', 'tech')
          AND mg.code = 'audit'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE menu_group_id IN (SELECT id FROM menu_groups WHERE code = 'audit');
        """
    )
    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE menu_group_id IN (SELECT id FROM menu_groups WHERE code = 'audit');
        """
    )
    op.execute("DELETE FROM menu_groups WHERE code = 'audit';")
    # audit:read fica: vem do seed e é anterior a esta migration
