"""producer role: add order:produce, remove order:read; remove seller menu from admin

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
Create Date: producer role update

"""
from alembic import op


revision = "b1c2d3e4f5a6"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Permissão order:produce ──────────────────────────────────────────
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('order:produce', 'Produce orders (producer screen)')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # Remove order:read do order_producer — usa order:produce agora
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_producer')
          AND permission_id = (SELECT id FROM permissions WHERE code = 'order:read');
        """
    )

    # Dá order:produce ao order_producer
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'order_producer' AND p.code = 'order:produce'
        ON CONFLICT DO NOTHING;
        """
    )

    # Dá order:produce ao admin também
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'admin' AND p.code = 'order:produce'
        ON CONFLICT DO NOTHING;
        """
    )

    # ── Menu group "producer" ────────────────────────────────────────────
    op.execute(
        """
        INSERT INTO menu_groups (code, name, description)
        VALUES ('producer', 'Produção', 'Tela de produção')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'producer' AND p.code = 'order:produce'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )

    # Associa producer group ao order_producer
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'order_producer' AND mg.code = 'producer'
        ON CONFLICT DO NOTHING;
        """
    )

    # Associa producer group ao admin
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'admin' AND mg.code = 'producer'
        ON CONFLICT DO NOTHING;
        """
    )

    # ── Remove seller menu group do admin (admin cria pedidos pela tela de pedidos) ──
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'admin')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'seller');
        """
    )

    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'admin')
          AND permission_id = (SELECT id FROM permissions WHERE code = 'order:list');
        """
    )


def downgrade() -> None:
    # Restaura seller no admin
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'admin' AND mg.code = 'seller'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'admin' AND p.code = 'order:list'
        ON CONFLICT DO NOTHING;
        """
    )

    # Remove producer do admin e order_producer
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE menu_group_id = (SELECT id FROM menu_groups WHERE code = 'producer');
        """
    )
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (SELECT id FROM permissions WHERE code = 'order:produce');
        """
    )

    # Restaura order:read no order_producer
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'order_producer' AND p.code = 'order:read'
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE menu_group_id = (SELECT id FROM menu_groups WHERE code = 'producer');
        """
    )
    op.execute("DELETE FROM menu_groups WHERE code = 'producer';")
    op.execute("DELETE FROM permissions WHERE code = 'order:produce';")
