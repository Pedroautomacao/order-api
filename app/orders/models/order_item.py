from decimal import Decimal

from sqlalchemy import ForeignKey, Enum, Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import AuditMixin
from app.orders.enums import OrderItemStatus


class OrderItem(Base, AuditMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Preço no momento em que o pedido foi feito. Congelado aqui porque o
    # produto muda de preço e o pedido não pode mudar junto — e porque o admin
    # pode dar desconto exclusivo sem mexer no preço de tabela.
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        server_default="0",
        nullable=False,
    )

    produced_quantity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Real produced quantity informed by producer",
    )

    status: Mapped[OrderItemStatus] = mapped_column(
        Enum(OrderItemStatus),
        default=OrderItemStatus.AWAITING,
        nullable=False,
        index=True,
    )

    @property
    def total_price(self) -> Decimal:
        """Valor da linha: preço congelado × quantidade pedida."""
        return Decimal(str(self.unit_price or 0)) * Decimal(str(self.quantity or 0))

    # 🔗 RELATIONSHIPS
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    work_items = relationship(
        "WorkItem",
        back_populates="order_item",
        cascade="all, delete-orphan",
    )
