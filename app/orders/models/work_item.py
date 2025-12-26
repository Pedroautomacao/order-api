from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import AuditMixin


class WorkItem(Base, AuditMixin):
    __tablename__ = "work_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id"),
        nullable=False,
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    time_to_produced_secs: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # 🔗 RELATIONSHIPS
    order_item = relationship("OrderItem", back_populates="work_items")
    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    order = relationship(
        "Order",
        foreign_keys=[order_id],
    )
