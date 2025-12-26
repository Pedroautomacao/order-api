from alembic import op


# revision identifiers, used by Alembic.
revision = "xxxx_seed_roles_permissions"
down_revision = "570e9b99bc07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ROLES
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

    # PERMISSIONS
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES
            -- CLIENT
            ('client:create', 'Create client'),
            ('client:update', 'Update client'),
            ('client:delete', 'Delete client'),

            -- PRODUCT
            ('product:create', 'Create product'),
            ('product:update', 'Update product'),
            ('product:delete', 'Delete product'),

            -- ORDER (ADMIN ACTIONS)
            ('order:reset_production', 'Reset order production'),
            ('order:set_priority', 'Set order priority'),

            -- USER
            ('user:create', 'Create user'),
            ('user:update', 'Update user'),
            ('user:reset_password', 'Reset user password'),
            ('user:delete', 'Delete user'),

            -- AUDIT
            ('audit:read', 'Read audit logs')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # ADMIN GETS ALL PERMISSIONS
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
    # REMOVE ROLE-PERMISSION LINKS
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id IN (
            SELECT id FROM roles WHERE name = 'admin'
        );
        """
    )

    # REMOVE PERMISSIONS
    op.execute(
        """
        DELETE FROM permissions
        WHERE code IN (
            'client:create',
            'client:update',
            'client:delete',
            'product:create',
            'product:update',
            'product:delete',
            'order:reset_production',
            'order:set_priority',
            'user:create',
            'user:update',
            'user:reset_password',
            'user:delete',
            'audit:read'
        );
        """
    )

    # REMOVE ROLES
    op.execute(
        """
        DELETE FROM roles
        WHERE name IN ('tech', 'admin', 'order_creator', 'order_producer');
        """
    )
