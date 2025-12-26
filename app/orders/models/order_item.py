from sqlalchemy import ForeignKey, Enum, Float
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

    # 🔗 RELATIONSHIPS
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    work_items = relationship(
        "WorkItem",
        back_populates="order_item",
        cascade="all, delete-orphan",
    )
