"""payment method, credit limit and paid flag

- products.unit_price
- clients.allow_cash / allow_credit / credit_limit
- orders.payment_method (enum) / is_paid / total_amount
- permission order:mark_paid (assigned to 'orders' menu group)

Revision ID: c5d6e7f8a9b0
Revises: f1a2b3c4d5e6
Create Date: 2026-07-21

"""
from alembic import op
import sqlalchemy as sa

revision = "c5d6e7f8a9b0"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- products: preço unitário ---
    op.add_column(
        "products",
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )

    # --- clients: meios de pagamento + limite de crédito ---
    op.add_column(
        "clients",
        sa.Column("allow_cash", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "clients",
        sa.Column("allow_credit", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "clients",
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )

    # --- orders: forma de pagamento, pago, total ---
    # NB: usamos os NOMES dos membros como labels (CASH/CREDIT), mesmo padrão do
    # enum orderstatus do projeto (SQLAlchemy grava o nome do membro, não o value).
    payment_method = sa.Enum("CASH", "CREDIT", name="paymentmethod")
    payment_method.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "orders",
        sa.Column(
            "payment_method",
            payment_method,
            nullable=False,
            server_default="CASH",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "orders",
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )

    # --- permissão: marcar pedido como pago (só admin, via grupo 'orders') ---
    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('order:mark_paid', 'Marcar pedido como pago')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO menu_group_permissions (menu_group_id, permission_id)
        SELECT mg.id, p.id
        FROM menu_groups mg CROSS JOIN permissions p
        WHERE mg.code = 'orders' AND p.code = 'order:mark_paid'
        ON CONFLICT (menu_group_id, permission_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM menu_group_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'order:mark_paid');
        """
    )
    op.execute("DELETE FROM permissions WHERE code = 'order:mark_paid';")

    op.drop_column("orders", "total_amount")
    op.drop_column("orders", "is_paid")
    op.drop_column("orders", "payment_method")
    sa.Enum(name="paymentmethod").drop(op.get_bind(), checkfirst=True)

    op.drop_column("clients", "credit_limit")
    op.drop_column("clients", "allow_credit")
    op.drop_column("clients", "allow_cash")

    op.drop_column("products", "unit_price")
