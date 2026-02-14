"""add product:read permission and assign to admin

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: product read

"""
from alembic import op


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('product:read', 'Read/list products')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin'
          AND p.code = 'product:read'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (SELECT id FROM permissions WHERE code = 'product:read');
        """
    )
    op.execute(
        """
        DELETE FROM permissions WHERE code = 'product:read';
        """
    )
