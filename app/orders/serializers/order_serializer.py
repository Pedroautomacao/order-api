from app.orders.schemas.order_schema import OrderResponse
from app.orders.utils.split_order_item import split_order_items


def serialize_order(order) -> OrderResponse:
    produced_items, current_item = split_order_items(order)

    produced_items.sort(
        key=lambda i: i.product.name.lower()
    )

    return OrderResponse(
        id=order.id,
        priority=order.priority,
        status=order.status,
        scheduled_date=order.scheduled_date,

        produced_items=produced_items,
        current_item=current_item,

        can_finish=current_item is None,
    )
