"""add order:read and order:bill to fiscal role

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: fiscal screen

"""
from alembic import op


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'fiscal'
          AND p.code IN ('order:read', 'order:bill')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'fiscal')
          AND permission_id IN (SELECT id FROM permissions WHERE code IN ('order:read', 'order:bill'));
        """
    )
