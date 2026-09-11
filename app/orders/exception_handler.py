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
    def __init__(self, scheduled_date: date, minima: date | None = None):
        # "no passado" deixou de descrever o caso: depois das 16h de São Paulo
        # hoje também é recusado, e sem dizer a data mínima o usuário não sabe
        # o que escolher.
        if minima and minima > scheduled_date:
            mensagem = (
                f"Data de entrega {scheduled_date.strftime('%d/%m/%Y')} indisponível. "
                f"A primeira data possível é {minima.strftime('%d/%m/%Y')} — "
                f"pedidos para o mesmo dia só até as 16h."
            )
        else:
            mensagem = (
                f"Data de entrega {scheduled_date.strftime('%d/%m/%Y')} indisponível."
            )
        super().__init__(mensagem)


class OrderCanceledDuringProductionException(DomainException):
    """O pedido foi cancelado enquanto o produtor trabalhava nele.

    Sem esta exceção o produtor recebia "pedido não atribuído", porque o
    cancelamento limpa o assigned_user_id — mensagem que não diz o que houve
    nem o que fazer.
    """

    status_code = 409

    def __init__(self, order_id: int):
        super().__init__(
            f"O pedido #{order_id} foi cancelado durante a produção. "
            f"A produção foi encerrada e o pedido ficou parado como estava."
        )


class DuplicateOrderForClientException(DomainException):
    def __init__(self):
        super().__init__(
            "Client already has an active order with the same items for this date"
        )


class NoOrderAvailableException(DomainException):
    status_code = 404

    def __init__(self):
        super().__init__(
            "Não há pedidos aguardando produção para hoje."
        )


class OrderNotFinishedException(DomainException):
    def __init__(self):
        super().__init__(
            "Ainda há itens não produzidos neste pedido."
        )


class OrderNotInProductionException(DomainException):
    """O pedido saiu de produção enquanto a tela do produtor seguia aberta."""

    def __init__(self):
        super().__init__(
            "Este pedido não está mais em produção. Recarregue a tela."
        )


class OrderNotFoundException(DomainException):
    status_code = 404

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
            "Informe uma quantidade produzida maior que zero."
        )


class OrderItemNotFoundException(DomainException):
    status_code = 404

    def __init__(self, item_id: int):
        super().__init__(f"Order item {item_id} not found")


class InvalidOrderItemStateException(DomainException):
    def __init__(self, item_id: int, expected: str, current: str):
        super().__init__(
            "Este item já foi atualizado por outra tela. "
            "Recarregue para ver a situação atual."
        )
        self.item_id = item_id
        self.expected = expected
        self.current = current


class OrderNotAssignedToUserException(DomainException):
    status_code = 404

    def __init__(self):
        super().__init__("Este pedido não está mais atribuído a você.")


class WorkItemNotFoundException(DomainException):
    status_code = 404

    def __init__(self):
        super().__init__("Open work item not found")


class PaymentMethodNotAllowedException(DomainException):
    def __init__(self, method_label: str):
        super().__init__(
            f"Este cliente não aceita pagamento {method_label}."
        )


class CreditLimitExceededException(DomainException):
    """Levantada quando um pedido a prazo estoura o limite de crédito do cliente."""

    def __init__(self, *, limit, outstanding, order_amount):
        self.limit = limit
        self.outstanding = outstanding
        self.order_amount = order_amount
        available = limit - outstanding
        super().__init__(
            "Limite de crédito atingido. "
            f"Limite R$ {limit:.2f}, em aberto R$ {outstanding:.2f}, "
            f"disponível R$ {available:.2f}, este pedido R$ {order_amount:.2f}. "
            "Só o administrador pode liberar: aumentar o limite ou marcar um pedido como pago."
        )
