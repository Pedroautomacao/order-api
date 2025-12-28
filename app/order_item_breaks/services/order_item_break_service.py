from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.order_item_breaks.models import OrderItemBreak


class OrderItemBreakService:
    @staticmethod
    def list(
        db: Session,
        *,
        order_id: UUID | None = None,
        order_item_id: UUID | None = None,
    ):
        stmt = select(OrderItemBreak).where(
            OrderItemBreak.is_deleted.is_(False)
        )

        if order_id:
            stmt = stmt.where(OrderItemBreak.order_id == order_id)

        if order_item_id:
            stmt = stmt.where(OrderItemBreak.order_item_id == order_item_id)

        stmt = stmt.order_by(OrderItemBreak.created_at.desc())

        return db.execute(stmt).scalars().all()
