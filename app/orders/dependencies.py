from sqlalchemy.orm import Session

from app.orders.models.order import Order
from app.orders.exception_handler import OrderNotFoundException, OrderItemNotFoundException
from app.orders.models.order_item import OrderItem


def get_order_or_404(
    db: Session,
    order_id: int,
) -> Order:
    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.is_deleted.is_(False),
        )
        .first()
    )

    if not order:
        raise OrderNotFoundException(order_id)

    return order


def get_order_item_or_404(
    db: Session,
    order_item_id: int,
) -> OrderItem:
    item = (
        db.query(OrderItem)
        .filter(
            OrderItem.id == order_item_id,
            OrderItem.is_deleted.is_(False),
        )
        .first()
    )

    if not item:
        raise OrderItemNotFoundException(order_item_id)

    return item
