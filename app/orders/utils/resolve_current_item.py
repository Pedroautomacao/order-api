from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem


def resolve_current_item(order: Order) -> OrderItem | None:
    # 1️⃣ item já em produção
    for item in order.items:
        if item.status == "Producing":
            return item

    # 2️⃣ próximo item aguardando
    awaiting_items = [
        item for item in order.items
        if item.status == "Awaiting"
    ]

    if not awaiting_items:
        return None

    return sorted(
        awaiting_items,
        key=lambda i: i.product.name.lower()
    )[0]
