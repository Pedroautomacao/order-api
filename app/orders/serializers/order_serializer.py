from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.schemas.order_schema import OrderResponse, OrderListResponse
from app.orders.utils.split_order_item import split_order_items


def _item_sort_key(item):
    """Ordena por nome do produto. Order.items não tem ordenação definida, então
    sem isso a tabela de itens muda de ordem entre um F5 e outro."""
    product = getattr(item, "product", None)
    return (getattr(product, "name", "") or "").lower()


def _payment_method(order):
    method = order.payment_method
    return method.value if hasattr(method, "value") else method


def serialize_order_list_item(order) -> OrderListResponse:
    return OrderListResponse(
        id=order.id,
        priority=order.priority,
        status=order.status,
        scheduled_date=order.scheduled_date,
        client_id=order.client_id,
        client=order.client,
        payment_method=_payment_method(order),
        is_paid=order.is_paid,
        total_amount=order.total_amount,
    )


def serialize_order(order) -> OrderResponse:
    items = sorted(order.items or [], key=_item_sort_key)

    produced_items, current_item = split_order_items(order)
    produced_items.sort(key=_item_sort_key)

    return OrderResponse(
        id=order.id,
        priority=order.priority,
        status=order.status,
        scheduled_date=order.scheduled_date,
        client_id=order.client_id,
        client=order.client,
        created_by_user_id=order.created_by_user_id,

        payment_method=_payment_method(order),
        is_paid=order.is_paid,
        total_amount=order.total_amount,

        items=items,

        produced_items=produced_items,
        current_item=current_item,
        total_items=len(items),

        # Mesma regra do servidor em OrderFinishService.finish_order: só um
        # pedido em produção, com itens, e todos eles produzidos.
        can_finish=(
            order.status == OrderStatus.PRODUCING
            and bool(items)
            and all(i.status == OrderItemStatus.PRODUCED for i in items)
        ),
    )
