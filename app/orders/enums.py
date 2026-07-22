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


class PaymentMethod(str, enum.Enum):
    CASH = "Cash"      # À vista
    CREDIT = "Credit"  # A prazo
