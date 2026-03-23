"""seller role: remove order:read, add seller menu group

Revision ID: a9b0c1d2e3f4
Revises: b8c9d0e1f2a3
Create Date: seller role update

"""
from alembic import op


revision = "a9b0c1d2e3f4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove order:read from order_creator — vendedor usa /orders/seller (order:list)
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_creator')
          AND permission_id = (SELECT id FROM permissions WHERE code = 'order:read');
        """
    )

    # Garante que order:list existe
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('order:list', 'List own orders (seller)')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # Garante que order_creator tem order:list
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'order_creator'
          AND p.code = 'order:list'
        ON CONFLICT DO NOTHING;
        """
    )

    # Adiciona menu group "seller" para a rota /admin/seller
    op.execute(
        """
        INSERT INTO menu_groups (code, name, description)
        VALUES ('seller', 'Meus Pedidos', 'Tela de pedidos do vendedor')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # Vincula o menu group "seller" à permissão order:list
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg
        CROSS JOIN permissions p
        WHERE mg.code = 'seller'
          AND p.code = 'order:list'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )

    # Garante que order:create existe e vincula ao menu group "seller"
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('order:create', 'Create orders')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg
        CROSS JOIN permissions p
        WHERE mg.code = 'seller'
          AND p.code = 'order:create'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )

    # Associa o menu group "seller" ao role order_creator
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r
        CROSS JOIN menu_groups mg
        WHERE r.name = 'order_creator'
          AND mg.code = 'seller'
        ON CONFLICT DO NOTHING;
        """
    )

    # Remove o menu group "orders" do order_creator (não vê mais todos os pedidos)
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_creator')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'orders');
        """
    )

    # Admin também recebe order:list (para acessar /admin/seller)
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin'
          AND p.code = 'order:list'
        ON CONFLICT DO NOTHING;
        """
    )

    # Associa o menu group "seller" ao role admin
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r
        CROSS JOIN menu_groups mg
        WHERE r.name = 'admin'
          AND mg.code = 'seller'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    # Restaura order:read no order_creator
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'order_creator'
          AND p.code = 'order:read'
        ON CONFLICT DO NOTHING;
        """
    )

    # Remove order:list do order_creator
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_creator')
          AND permission_id = (SELECT id FROM permissions WHERE code = 'order:list');
        """
    )

    # Remove menu group seller do order_creator
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'order_creator')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'seller');
        """
    )

    # Restaura menu group orders no order_creator
    op.execute(
        """
        INSERT INTO role_menu_groups (role_id, menu_group_id)
        SELECT r.id, mg.id
        FROM roles r
        CROSS JOIN menu_groups mg
        WHERE r.name = 'order_creator'
          AND mg.code = 'orders'
        ON CONFLICT DO NOTHING;
        """
    )

    # Remove order:list e menu group seller do admin
    op.execute(
        """
        DELETE FROM role_menu_groups
        WHERE role_id = (SELECT id FROM roles WHERE name = 'admin')
          AND menu_group_id = (SELECT id FROM menu_groups WHERE code = 'seller');
        """
    )
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'admin')
          AND permission_id = (SELECT id FROM permissions WHERE code = 'order:list');
        """
    )

    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE menu_group_id = (SELECT id FROM menu_groups WHERE code = 'seller');
        """
    )
    op.execute("DELETE FROM menu_groups WHERE code = 'seller';")
    op.execute("DELETE FROM permissions WHERE code = 'order:create';")
