"""fix menu group permissions: add missing crud perms to clients/products/orders

Revision ID: f1a2b3c4d5e6
Revises: e08d62adc522
Create Date: 2026-03-22

"""
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e08d62adc522"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE
            (mg.code = 'clients'  AND p.code IN ('client:create','client:update','client:delete'))
            OR (mg.code = 'products' AND p.code IN ('product:create','product:update','product:delete','unit:create','unit:update','unit:delete','unit:list'))
            OR (mg.code = 'orders'   AND p.code IN ('order:bill','order:cancel'))
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
    """)


def downgrade() -> None:
    pass
