from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.clients.exception_handler import ClientNotFoundException
from app.clients.models.client import Client
from app.core.services.base_atomic_service import BaseAtomicService
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


class OrderUpdateService(BaseAtomicService):
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

        if data.scheduled_date < date.today():
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

        # replace items
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

        AuditService.log(
            db=db,
            action="order:update",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=f"Order {order.id} updated by {current_user.username}",
        )

        db.commit()
        db.refresh(order)
        return order
