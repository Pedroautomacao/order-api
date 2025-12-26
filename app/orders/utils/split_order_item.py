def split_order_items(order):
    produced_items = []
    current_item = None

    for item in order.items:
        if item.status == "Produced":
            produced_items.append(item)
        elif item.status == "Producing":
            current_item = item

    return produced_items, current_item
