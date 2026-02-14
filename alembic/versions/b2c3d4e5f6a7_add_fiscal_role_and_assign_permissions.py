from alembic import op


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role 'fiscal' (for fiscal screen - permissions to be added later)
    op.execute(
        """
        INSERT INTO roles (name)
        VALUES ('fiscal')
        ON CONFLICT (name) DO NOTHING;
        """
    )

    # Vendedor (order_creator): client:read, order:create, order:read, order:list
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'order_creator'
          AND p.code IN ('client:read', 'order:create', 'order:read', 'order:list')
        ON CONFLICT DO NOTHING;
        """
    )

    # Produtor (order_producer): order:read (assign-next, finish use order:read)
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'order_producer'
          AND p.code = 'order:read'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_creator')
          AND permission_id IN (SELECT id FROM permissions WHERE code IN ('client:read', 'order:create', 'order:read', 'order:list'));
        """
    )
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_producer')
          AND permission_id = (SELECT id FROM permissions WHERE code = 'order:read');
        """
    )
    op.execute(
        """
        DELETE FROM roles WHERE name = 'fiscal';
        """
    )
