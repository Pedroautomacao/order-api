from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.orders.enums import OrderStatus, PaymentMethod
from app.orders.exception_handler import (
    CreditLimitExceededException,
    PaymentMethodNotAllowedException,
)
from app.orders.models.order import Order
from app.products.models.product import Product


class CreditService:
    """Regras de crédito a prazo do cliente.

    O limite representa a soma máxima de pedidos **a prazo ainda não pagos**
    (payment_method = Credit, is_paid = False, não cancelados) que um cliente
    pode ter em aberto. Pedidos à vista não contam.
    """

    @staticmethod
    def outstanding_credit(
        db: Session,
        client_id: int,
        *,
        exclude_order_id: int | None = None,
    ) -> Decimal:
        q = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.client_id == client_id,
            Order.payment_method == PaymentMethod.CREDIT,
            Order.is_paid.is_(False),
            Order.status != OrderStatus.CANCELED,
            Order.is_deleted.is_(False),
        )
        if exclude_order_id is not None:
            q = q.filter(Order.id != exclude_order_id)
        return Decimal(str(q.scalar() or 0))

    @staticmethod
    def compute_order_amount(db: Session, items) -> Decimal:
        """Σ(preço unitário × quantidade) dos itens do pedido."""
        total = Decimal("0")
        for item in items:
            product = (
                db.query(Product)
                .filter(Product.id == item.product_id)
                .first()
            )
            if product is None:
                continue
            total += Decimal(str(product.unit_price or 0)) * Decimal(str(item.quantity))
        return total

    @staticmethod
    def validate_payment_method(client: Client, payment_method: PaymentMethod) -> None:
        if payment_method == PaymentMethod.CASH and not client.allow_cash:
            raise PaymentMethodNotAllowedException("à vista")
        if payment_method == PaymentMethod.CREDIT and not client.allow_credit:
            raise PaymentMethodNotAllowedException("a prazo")

    @staticmethod
    def check_credit_or_raise(
        db: Session,
        *,
        client: Client,
        payment_method: PaymentMethod,
        order_amount: Decimal,
        exclude_order_id: int | None = None,
    ) -> None:
        """Barra pedido a prazo que estoura o limite do cliente."""
        if payment_method != PaymentMethod.CREDIT:
            return
        outstanding = CreditService.outstanding_credit(
            db, client.id, exclude_order_id=exclude_order_id
        )
        limit = Decimal(str(client.credit_limit or 0))
        if outstanding + Decimal(str(order_amount)) > limit:
            raise CreditLimitExceededException(
                limit=limit,
                outstanding=outstanding,
                order_amount=Decimal(str(order_amount)),
            )
