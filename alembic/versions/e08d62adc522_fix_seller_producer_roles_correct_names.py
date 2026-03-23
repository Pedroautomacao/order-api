"""fix seller/producer roles using correct role names (Vendedor, Produtor, Admin)

Revision ID: e08d62adc522
Revises: b1c2d3e4f5a6
Create Date: 2026-03-22

"""
from alembic import op


revision = "e08d62adc522"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Permissões necessárias ──────────────────────────────────────────────
    op.execute("""
        INSERT INTO permissions (code, description)
        VALUES
            ('order:list',    'List own orders (seller)'),
            ('order:create',  'Create orders'),
            ('order:produce', 'Produce orders (producer screen)')
        ON CONFLICT (code) DO NOTHING;
    """)

    # ── Menu group seller ───────────────────────────────────────────────────
    op.execute("""
        INSERT INTO menu_groups (code, name, description)
        VALUES ('seller', 'Meus Pedidos', 'Tela de pedidos do vendedor')
        ON CONFLICT (code) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'seller' AND p.code IN ('order:list', 'order:create')
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
    """)

    # ── Menu group producer ─────────────────────────────────────────────────
    op.execute("""
        INSERT INTO menu_groups (code, name, description)
        VALUES ('producer', 'Produção', 'Tela de produção')
        ON CONFLICT (code) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'producer' AND p.code = 'order:produce'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
    """)

    # ── Vendedor: associar menu group seller ────────────────────────────────
    op.execute("""
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'Vendedor' AND mg.code = 'seller'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
    """)

    # ── Produtor: associar menu group producer ──────────────────────────────
    op.execute("""
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'Produtor' AND mg.code = 'producer'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Produtor' AND p.code = 'order:produce'
        ON CONFLICT DO NOTHING;
    """)

    # ── Admin: adicionar menu group producer ────────────────────────────────
    op.execute("""
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r CROSS JOIN menu_groups mg
        WHERE r.name = 'Admin' AND mg.code = 'producer'
        ON CONFLICT (role_id, menu_group_id) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Admin' AND p.code = 'order:produce'
        ON CONFLICT DO NOTHING;
    """)

    # ── Menu group orders do Admin: garantir permissões de criação/cancelamento
    op.execute("""
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'orders'
          AND p.code IN ('order:create', 'order:cancel', 'order:reset_production', 'order:set_priority')
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'Admin')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'producer');
    """)
    op.execute("""
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'Vendedor')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'seller');
    """)
    op.execute("""
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'Produtor')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'producer');
    """)
