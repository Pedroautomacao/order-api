"""move approve_production permission to the orders menu group

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-09-10

A c7d8e9f0a1b2 concedeu order:approve_production direto aos roles admin e Tech,
e isso não funciona: PermissionService.get_user_permissions ignora as permissões
diretas de um role que tenha grupos de menu, e os dois têm. A permissão nunca
resolveria.

A liberação de produção passa a pendurar no grupo de menu `orders` — o mesmo que
dá a tela de pedidos e as ações de editar (order:read, order:cancel, order:bill).
Quem pode mexer na tela passa a poder aprovar, e atribuir o grupo a um perfil novo
pela tela de "Menus por perfil" leva a permissão junto, sem migration.
"""
from alembic import op


revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg
        CROSS JOIN permissions p
        WHERE mg.code = 'orders'
          AND p.code = 'order:approve_production'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )

    # Limpa o grant direto da migration anterior: não surtia efeito para admin
    # nem Tech e só confundiria quem for ler as permissões do role.
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
            SELECT id FROM permissions WHERE code = 'order:approve_production'
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE permission_id = (
            SELECT id FROM permissions WHERE code = 'order:approve_production'
        );
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('admin', 'Tech')
          AND p.code = 'order:approve_production'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
        """
    )
