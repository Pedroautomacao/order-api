from alembic import op


revision = "a1b2c3d4e5f6"
down_revision = "xxxx_add_strategic_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add client:read permission (required for GET /clients/ list and get client)
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('client:read', 'Read/list clients')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    # Assign to admin role
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin' AND p.code = 'client:read'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (SELECT id FROM permissions WHERE code = 'client:read');
        """
    )
    op.execute(
        """
        DELETE FROM permissions WHERE code = 'client:read';
        """
    )
