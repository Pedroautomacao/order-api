from alembic import op


# revision identifiers, used by Alembic.
revision = "xxxxxxxxxxxx"
down_revision = "a51eafe489f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1️⃣ ROLES
    op.execute(
        """
        INSERT INTO roles (name)
        VALUES
            ('tech'),
            ('admin'),
            ('order_creator'),
            ('order_producer')
        ON CONFLICT (name) DO NOTHING;
        """
    )

    # 2️⃣ PERMISSIONS
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES
            ('order:reset_production', 'Reset order production'),
            ('order:set_priority', 'Set order production priority'),

            ('supplier:create', 'Create supplier'),
            ('supplier:update', 'Update supplier'),
            ('supplier:delete', 'Delete supplier'),

            ('product:create', 'Create product'),
            ('product:update', 'Update product'),
            ('product:delete', 'Delete product'),

            ('user:create', 'Create user'),
            ('user:update', 'Update user'),
            ('user:reset_password', 'Reset user password'),
            ('user:delete', 'Delete user')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # 3️⃣ ROLE → PERMISSIONS (ADMIN GETS ALL)
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    # Remove role-permission links
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id IN (
            SELECT id FROM roles WHERE name IN ('admin')
        );
        """
    )

    # Remove permissions
    op.execute(
        """
        DELETE FROM permissions
        WHERE code IN (
            'order:reset_production',
            'order:set_priority',
            'supplier:create',
            'supplier:update',
            'supplier:delete',
            'product:create',
            'product:update',
            'product:delete',
            'user:create',
            'user:update',
            'user:reset_password',
            'user:delete'
        );
        """
    )

    # Remove roles
    op.execute(
        """
        DELETE FROM roles
        WHERE name IN ('tech', 'admin', 'order_creator', 'order_producer');
        """
    )
