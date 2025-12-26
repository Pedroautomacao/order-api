from sqlalchemy.orm import Session
from app.orders.models.order import Order
from app.orders.enums import OrderStatus


def get_user_current_order(
    db: Session,
    *,
    user_id: int,
) -> Order | None:
    return (
        db.query(Order)
        .filter(
            Order.assigned_user_id == user_id,
            Order.status == OrderStatus.PRODUCING,
            Order.is_deleted.is_(False),
        )
        .first()
    )
