from sqlalchemy.orm import Session, selectinload

from app.orders.models.order import Order
from app.orders.exception_handler import OrderNotFoundException, OrderItemNotFoundException
from app.orders.models.order_item import OrderItem
from app.products.models.product import Product


def with_detail_relations(query):
    """Carrega a cadeia que serialize_order percorre (itens -> produto ->
    unidade). Sem isso cada item vira duas queries extras."""
    return query.options(
        selectinload(Order.client),
        selectinload(Order.items)
        .selectinload(OrderItem.product)
        .selectinload(Product.unit_of_measure),
    )


def get_order_or_404(
    db: Session,
    order_id: int,
) -> Order:
    order = (
        with_detail_relations(db.query(Order))
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
