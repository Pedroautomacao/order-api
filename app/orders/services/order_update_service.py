from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.clients.exception_handler import ClientNotFoundException
from app.clients.models.client import Client
from app.order_item_breaks.models import OrderItemBreak
from app.database.atomic import atomic
from app.orders.enums import OrderStatus
from app.orders.exception_handler import (
    DuplicateProductInOrderException,
    InvalidScheduledDateException,
    DuplicateOrderForClientException,
)
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.products.exception_handler import ProductNotFoundException
from app.products.models.product import Product
from app.users.models.user import User
from app.core.time import min_scheduled_date


class OrderUpdateService:
    @staticmethod
    def update(
        db: Session,
        *,
        order: Order,
        data,
        current_user: User,
    ) -> Order:
        if order.created_by_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para editar este pedido.",
            )

        if order.status != OrderStatus.AWAITING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas pedidos em Aguardando podem ser editados.",
            )

        # Mesma regra do create: sem esta guarda um PUT com lista vazia
        # apaga todos os itens do pedido e zera o total.
        if not data.items:
            raise ValueError("Order must have at least one item")

        if data.scheduled_date < min_scheduled_date():
            raise InvalidScheduledDateException(data.scheduled_date)

        client = (
            db.query(Client)
            .filter(
                Client.id == data.client_id,
                Client.is_deleted.is_(False),
            )
            .first()
        )
        if not client:
            raise ClientNotFoundException(data.client_id)
        if not client.is_active:
            raise ValueError("Cliente inativo não pode receber pedidos.")

        product_ids = [item.product_id for item in data.items]
        if len(product_ids) != len(set(product_ids)):
            for pid in product_ids:
                if product_ids.count(pid) > 1:
                    raise DuplicateProductInOrderException(pid)

        existing_orders = (
            db.query(Order)
            .filter(
                Order.client_id == client.id,
                Order.scheduled_date == data.scheduled_date,
                Order.status != OrderStatus.CANCELED,
                Order.id != order.id,
            )
            .all()
        )
        requested_product_ids = {item.product_id for item in data.items}
        for existing in existing_orders:
            if {i.product_id for i in existing.items} == requested_product_ids:
                raise DuplicateOrderForClientException()

        # forma de pagamento + validação de crédito (exclui o próprio pedido do "em aberto")
        from app.orders.enums import PaymentMethod
        from app.orders.services.credit_service import CreditService

        payment_method = getattr(data, "payment_method", None) or order.payment_method
        if not isinstance(payment_method, PaymentMethod):
            payment_method = PaymentMethod(payment_method)
        CreditService.validate_payment_method(client, payment_method)

        total_amount = CreditService.compute_order_amount(db, data.items)
        CreditService.check_credit_or_raise(
            db,
            client=client,
            payment_method=payment_method,
            order_amount=total_amount,
            exclude_order_id=order.id,
        )

        with atomic(db):
            # replace items — as quebras referenciam order_items, então
            # precisam sair antes ou o DELETE estoura violação de FK
            item_ids = [i.id for i in order.items]
            if item_ids:
                (
                    db.query(OrderItemBreak)
                    .filter(OrderItemBreak.order_item_id.in_(item_ids))
                    .delete(synchronize_session=False)
                )

            for item in order.items:
                db.delete(item)
            db.flush()

            for item_data in data.items:
                product = (
                    db.query(Product)
                    .filter(
                        Product.id == item_data.product_id,
                        Product.is_deleted.is_(False),
                    )
                    .first()
                )
                if not product:
                    raise ProductNotFoundException(item_data.product_id)

                db.add(OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item_data.quantity,
                ))

            order.client_id = client.id
            order.scheduled_date = data.scheduled_date
            order.priority = client.priority
            order.payment_method = payment_method
            order.total_amount = total_amount

            AuditService.log(
                db=db,
                action="order:update",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=(
                    f"Pedido #{order.id} editado: {len(data.items)} item(ns), "
                    f"entrega em {data.scheduled_date.strftime('%d/%m/%Y')}"
                ),
            )

        db.refresh(order)
        return order
