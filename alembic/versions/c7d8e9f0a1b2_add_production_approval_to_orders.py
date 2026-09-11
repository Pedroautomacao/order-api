"""add production approval to orders

Revision ID: c7d8e9f0a1b2
Revises: f8a9b0c1d2e3
Create Date: 2026-09-10

Todo pedido passa a carregar a liberação para produzir. Pedidos que já existem
entram como AWAITING (o server_default cobre as linhas antigas), então nada é
liberado para a fila sem alguém aprovar.
"""
from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


# O SQLAlchemy grava o NOME do membro do enum, não o valor — Enum(ProductionApproval)
# gera o tipo 'productionapproval' com estes rótulos.
PRODUCTION_APPROVAL = sa.Enum(
    "AWAITING",
    "APPROVED",
    "RECUSED",
    name="productionapproval",
)


def upgrade() -> None:
    bind = op.get_bind()
    PRODUCTION_APPROVAL.create(bind, checkfirst=True)

    op.add_column(
        "orders",
        sa.Column(
            "production_approval",
            PRODUCTION_APPROVAL,
            nullable=False,
            server_default="AWAITING",
        ),
    )
    op.create_index(
        "ix_orders_production_approval",
        "orders",
        ["production_approval"],
    )

    op.execute(
        """
        INSERT INTO permissions (code, description)
        VALUES ('order:approve_production', 'Approve or recuse order production')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('admin', 'Tech')
          AND p.code = 'order:approve_production'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
            SELECT id FROM permissions WHERE code = 'order:approve_production'
        );
        """
    )
    op.execute(
        "DELETE FROM permissions WHERE code = 'order:approve_production';"
    )

    op.drop_index("ix_orders_production_approval", table_name="orders")
    op.drop_column("orders", "production_approval")
    PRODUCTION_APPROVAL.drop(op.get_bind(), checkfirst=True)
