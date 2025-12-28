from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import AuditMixin


class OrderItemBreak(Base, AuditMixin):
    __tablename__ = "order_item_breaks"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    order_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("order_items.id"),
        nullable=False,
        index=True,
    )

    expected_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )

    confirmed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )

    difference_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="expected_quantity - confirmed_quantity",
    )

    # relacionamentos somente leitura
    order = relationship("Order", viewonly=True)
    order_item = relationship("OrderItem", viewonly=True)
