from app.core.logging import logger
from app.orders.enums import OrderItemStatus


def split_order_items(order):
    """Recorte da tela do produtor: o que já saiu e o que está na bancada.

    Não é a lista completa de itens — item em Aguardando não aparece em nenhum
    dos dois. Quem precisa de todos os itens usa ``OrderResponse.items``.
    """
    produced_items = []
    producing_items = []

    for item in order.items:
        if item.status == OrderItemStatus.PRODUCED:
            produced_items.append(item)
        elif item.status == OrderItemStatus.PRODUCING:
            producing_items.append(item)

    if len(producing_items) > 1:
        # Estado inconsistente: só um item por vez deveria estar em produção.
        # Antes o último do laço sobrescrevia os anteriores em silêncio.
        logger.warning(
            "Order %s has %s items in production at once (ids=%s); "
            "using the first one",
            order.id,
            len(producing_items),
            [i.id for i in producing_items],
        )

    current_item = min(producing_items, key=lambda i: i.id, default=None)

    return produced_items, current_item
