"""snapshot do preço unitário no item do pedido

Revision ID: a1b2c3d4e5f7
Revises: f0a1b2c3d4e5
Create Date: 2026-09-11

order_items não guardava preço: o detalhe do pedido mostrava products.unit_price,
o preço ATUAL do produto. Quando o produto mudava de preço, a tela passava a
mentir sobre o que foi vendido e não fechava com orders.total_amount, que é
snapshot do momento da criação.

A coluna também é o que permite dar desconto exclusivo num pedido sem mexer no
preço de tabela do produto.

Backfill: os itens que já existem recebem o preço atual do produto. É a melhor
aproximação disponível — o valor cobrado de verdade não foi registrado em
lugar nenhum, então pedido antigo cujo produto mudou de preço fica com o valor
de hoje, e a soma dos itens pode não bater com o total_amount do pedido.
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f7"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nullable primeiro para o backfill rodar; NOT NULL depois
    op.add_column(
        "order_items",
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
    )
    op.execute(
        """
        UPDATE order_items oi
        SET unit_price = COALESCE(p.unit_price, 0)
        FROM products p
        WHERE p.id = oi.product_id;
        """
    )
    # item órfão de produto não deveria existir, mas o NOT NULL abaixo não
    # perdoa: zera o que sobrar em vez de derrubar a migration
    op.execute("UPDATE order_items SET unit_price = 0 WHERE unit_price IS NULL;")
    op.alter_column(
        "order_items",
        "unit_price",
        existing_type=sa.Numeric(12, 2),
        nullable=False,
        server_default="0",
    )

    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('order:update', 'Edit order items, quantities and sold price')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'orders' AND p.code = 'order:update'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE permission_id = (SELECT id FROM permissions WHERE code = 'order:update');
        """
    )
    op.execute("DELETE FROM permissions WHERE code = 'order:update';")
    op.drop_column("order_items", "unit_price")
