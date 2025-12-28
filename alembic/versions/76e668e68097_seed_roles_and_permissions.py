from alembic import op


# revision identifiers, used by Alembic.
revision = "xxxx_seed_roles_permissions"
down_revision = "570e9b99bc07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===============================
    # ROLES
    # ===============================
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

    # ===============================
    # PERMISSIONS
    # ===============================
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

            -- UNIT OF MEASURE
            ('unit:create', 'Create unit of measure'),
            ('unit:update', 'Update unit of measure'),
            ('unit:delete', 'Delete unit of measure'),
            ('unit:list', 'List units of measure'),

            -- ORDER
            ('order:create', 'Create order'),
            ('order:read', 'View order'),
            ('order:list', 'List orders'),
            ('order:cancel', 'Cancel order'),
            ('order:reset_production', 'Reset order production'),
            ('order:set_priority', 'Set order priority'),
            ('order:bill', 'Set order billed'),

            -- ORDER ITEM BREAK
            ('order_item_break:read', 'Read order item breaks'),
            ('order_item_break:create', 'Create order item break'),
            ('order_item_break:update', 'Update order item break'),
            ('order_item_break:delete', 'Delete order item break'),

            -- RANKINGS
            ('rankings:read', 'Read rankings dashboards'),

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

    # ===============================
    # ADMIN GETS ALL PERMISSIONS
    # ===============================
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
    # ===============================
    # REMOVE ROLE-PERMISSION LINKS
    # ===============================
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id IN (
            SELECT id FROM roles WHERE name = 'admin'
        );
        """
    )

    # ===============================
    # REMOVE PERMISSIONS
    # ===============================
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

            'unit:create',
            'unit:update',
            'unit:delete',
            'unit:list',

            'order:create',
            'order:read',
            'order:list',
            'order:cancel',
            'order:reset_production',
            'order:set_priority',
            'order:bill',

            'order_item_break:read',
            'order_item_break:create',
            'order_item_break:update',
            'order_item_break:delete',

            'rankings:read',

            'user:create',
            'user:update',
            'user:reset_password',
            'user:delete',

            'audit:read'
        );
        """
    )

    # ===============================
    # REMOVE ROLES
    # ===============================
    op.execute(
        """
        DELETE FROM roles
        WHERE name IN ('tech', 'admin', 'order_creator', 'order_producer');
        """
    )
