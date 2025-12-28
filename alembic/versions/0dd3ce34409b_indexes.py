from alembic import op


# revision identifiers, used by Alembic.
revision = "xxxx_add_strategic_indexes"
down_revision = "71a2ca0f8aec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =====================================================
    # ORDERS
    # =====================================================

    # Dashboard / assign / listagem por data + status
    op.create_index(
        "ix_orders_scheduled_date_status",
        "orders",
        ["scheduled_date", "status"],
    )

    # Quem está produzindo
    op.create_index(
        "ix_orders_assigned_user_id",
        "orders",
        ["assigned_user_id"],
    )

    # Billing + dashboard histórico
    op.create_index(
        "ix_orders_status_updated_at",
        "orders",
        ["status", "updated_at"],
    )

    # =====================================================
    # WORK_ORDERS
    # =====================================================

    # Métricas por período
    op.create_index(
        "ix_work_orders_started_at",
        "work_orders",
        ["started_at"],
    )

    # Produção por usuário
    op.create_index(
        "ix_work_orders_user_id_started_at",
        "work_orders",
        ["user_id", "started_at"],
    )

    # =====================================================
    # WORK_ITEMS
    # =====================================================

    # Métricas de item
    op.create_index(
        "ix_work_items_started_at",
        "work_items",
        ["started_at"],
    )

    # =====================================================
    # ORDER_ITEM_BREAKS
    # =====================================================

    # Dashboard de perdas
    op.create_index(
        "ix_order_item_breaks_created_at",
        "order_item_breaks",
        ["created_at"],
    )

    # Perdas por período + produto
    op.create_index(
        "ix_order_item_breaks_created_at_order_item_id",
        "order_item_breaks",
        ["created_at", "order_item_id"],
    )


def downgrade() -> None:
    # =====================================================
    # DASHBOARD_SNAPSHOTS
    # =====================================================
    op.drop_index(
        "ix_dashboard_snapshots_generated_at",
        table_name="dashboard_snapshots",
    )

    # =====================================================
    # ORDER_ITEM_BREAKS
    # =====================================================
    op.drop_index(
        "ix_order_item_breaks_created_at_order_item_id",
        table_name="order_item_breaks",
    )
    op.drop_index(
        "ix_order_item_breaks_order_item_id",
        table_name="order_item_breaks",
    )
    op.drop_index(
        "ix_order_item_breaks_created_at",
        table_name="order_item_breaks",
    )

    # =====================================================
    # WORK_ITEMS
    # =====================================================
    op.drop_index(
        "ix_work_items_started_at",
        table_name="work_items",
    )

    # =====================================================
    # WORK_ORDERS
    # =====================================================
    op.drop_index(
        "ix_work_orders_user_id_started_at",
        table_name="work_orders",
    )
    op.drop_index(
        "ix_work_orders_started_at",
        table_name="work_orders",
    )

    # =====================================================
    # ORDERS
    # =====================================================
    op.drop_index(
        "ix_orders_status_updated_at",
        table_name="orders",
    )
    op.drop_index(
        "ix_orders_assigned_user_id",
        table_name="orders",
    )
    op.drop_index(
        "ix_orders_scheduled_date_status",
        table_name="orders",
    )
    op.drop_index(
        "ix_orders_status",
        table_name="orders",
    )
