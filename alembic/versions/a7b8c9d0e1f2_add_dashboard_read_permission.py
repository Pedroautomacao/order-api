"""add dashboard:read permission for dashboard screen

Revision ID: a7b8c9d0e1f2
Revises: f6e7a8b9c0d1
Create Date: dashboard has its own permission (audit:read is for future audit screen)

"""
from alembic import op


revision = "a7b8c9d0e1f2"
down_revision = "f6e7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('dashboard:read', 'Read dashboard overview')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin' AND p.code = 'dashboard:read'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (SELECT id FROM permissions WHERE code = 'dashboard:read');
        """
    )
    op.execute(
        """
        DELETE FROM permissions WHERE code = 'dashboard:read';
        """
    )
