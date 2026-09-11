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


class ProductionApproval(str, enum.Enum):
    """Libera ou barra a entrada do pedido na fila de produção.

    Todo pedido nasce em AWAITING: só entra na fila depois que alguém com
    ``order:approve_production`` aprova. A decisão é reversível nos dois
    sentidos, para corrigir engano.
    """

    AWAITING = "Awaiting"
    APPROVED = "Approved"
    RECUSED = "Recused"
