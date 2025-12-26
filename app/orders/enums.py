import enum


class OrderStatus(str, enum.Enum):
    AWAITING = "Awaiting"
    PRODUCING = "Producing"
    PRODUCED = "Produced"
    BILLED = "Billed"
    CANCELED = "Canceled"


class OrderItemStatus(str, enum.Enum):
    AWAITING = "Awaiting"
    PRODUCING = "Producing"
    PRODUCED = "Produced"
