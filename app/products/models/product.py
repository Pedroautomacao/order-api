from decimal import Decimal

from sqlalchemy import String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import AuditMixin


class Product(Base, AuditMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Preço unitário de venda",
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    sku: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    unit_of_measure_id: Mapped[int] = mapped_column(
        ForeignKey("units_of_measure.id"),
        nullable=False,
        index=True,
    )

    unit_of_measure = relationship("UnitOfMeasure")

    @property
    def unit(self):
        return self.unit_of_measure
