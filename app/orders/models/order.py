from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Enum, Date, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import AuditMixin
from app.orders.enums import OrderStatus, PaymentMethod


class Order(Base, AuditMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    priority: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
        index=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.AWAITING,
        nullable=False,
        index=True,
    )

    # Forma de pagamento escolhida na criação
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod),
        default=PaymentMethod.CASH,
        nullable=False,
    )

    # Pago (marcado pelo admin). Só pedidos a prazo não pagos contam no limite.
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Valor total do pedido no momento da criação (snapshot: Σ preço × qtd)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    # 🔗 RELATIONSHIPS
    client = relationship("Client")

    created_by = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    assigned_user = relationship(
        "User",
        foreign_keys=[assigned_user_id],
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
