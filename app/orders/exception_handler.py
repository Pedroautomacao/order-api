from datetime import date

from app.core.exceptions import DomainException


class OrderValidationException(DomainException):
    pass


class OrderAlreadyProducingException(DomainException):
    log_level = "error"

    def __init__(self, order_id: int):
        super().__init__(
            f"Order {order_id} already in production"
        )


class DuplicateProductInOrderException(DomainException):
    def __init__(self, product_id: int):
        super().__init__(
            f"Product {product_id} duplicated in order items"
        )


class InvalidScheduledDateException(DomainException):
    def __init__(self, scheduled_date: date):
        super().__init__(
            f"Scheduled date {scheduled_date} cannot be in the past"
        )


class DuplicateOrderForClientException(DomainException):
    def __init__(self):
        super().__init__(
            "Client already has an active order with the same items for this date"
        )


class NoOrderAvailableException(DomainException):
    def __init__(self):
        super().__init__(
            "No order available for this date"
        )


class OrderNotFinishedException(DomainException):
    def __init__(self):
        super().__init__(
            "Order not finished"
        )


class OrderNotFoundException(DomainException):
    def __init__(self, order_id: int):
        super().__init__(f"Order {order_id} not found")


class NoItemInProductionException(DomainException):
    def __init__(self):
        super().__init__(
            "No item for production"
        )


class InvalidProducedQuantityException(DomainException):
    def __init__(self):
        super().__init__(
            "Invalid product quantity"
        )


class OrderItemNotFoundException(DomainException):
    def __init__(self, item_id: int):
        super().__init__(f"Order item {item_id} not found")


class InvalidOrderItemStateException(DomainException):
    def __init__(self, item_id: int, expected: str, current: str):
        super().__init__(
            f"Order item {item_id} invalid state. "
            f"Expected {expected}, got {current}"
        )


class OrderNotAssignedToUserException(DomainException):
    def __init__(self):
        super().__init__("Order is not assigned to current user")


class WorkItemNotFoundException(DomainException):
    def __init__(self):
        super().__init__("Open work item not found")
