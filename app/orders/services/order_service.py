from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.exception_handler import ClientNotFoundException
from app.core.services.base_atomic_service import BaseAtomicService
from app.core.time import utcnow
from app.orders.exception_handler import DuplicateProductInOrderException, InvalidScheduledDateException, \
    DuplicateOrderForClientException, NoOrderAvailableException
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.enums import OrderStatus, OrderItemStatus
from app.clients.models.client import Client
from app.orders.models.work_item import WorkItem
from app.orders.models.work_order import WorkOrder
from app.orders.repositories.order_repository import get_user_current_order
from app.products.exception_handler import ProductNotFoundException
from app.products.models.product import Product
from app.audit.services.audit_service import AuditService
from app.users.models.user import User
from app.orders.utils.resolve_current_item import resolve_current_item


class OrderService(BaseAtomicService):
    @staticmethod
    def create(
        db: Session,
        *,
        data,
        current_user: User,
    ) -> Order:
        if not data.items:
            raise ValueError("Order must have at least one item")

        # 0️⃣ validar scheduled date
        from app.core.time import utcnow as _utcnow
        from datetime import timezone, timedelta
        _now_br = _utcnow().astimezone(timezone(timedelta(hours=-3)))
        _min_date = (
            date.today() + timedelta(days=1)
            if _now_br.hour >= 16
            else date.today()
        )
        if data.scheduled_date < _min_date:
            raise InvalidScheduledDateException(data.scheduled_date)

        # 1️⃣ Buscar client
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
            raise ValueError("Cliente inativo não pode receber novos pedidos")

        # 0️⃣ validar produtos duplicados no request
        product_ids = [item.product_id for item in data.items]
        if len(product_ids) != len(set(product_ids)):
            for pid in product_ids:
                if product_ids.count(pid) > 1:
                    raise DuplicateProductInOrderException(pid)

        # 🔍 validar pedido duplicado para o mesmo client no mesmo dia
        existing_orders = (
            db.query(Order)
            .filter(
                Order.client_id == client.id,
                Order.scheduled_date == data.scheduled_date,
                Order.status != OrderStatus.CANCELED,
            )
            .all()
        )

        requested_product_ids = {
            item.product_id for item in data.items
        }

        for existing_order in existing_orders:
            existing_product_ids = {
                item.product_id for item in existing_order.items
            }

            if existing_product_ids == requested_product_ids:
                raise DuplicateOrderForClientException()

        # 2️⃣ Criar order
        order = Order(
            client_id=client.id,
            created_by_user_id=current_user.id,
            priority=client.priority,
            status=OrderStatus.AWAITING,
            scheduled_date=data.scheduled_date,
        )

        db.add(order)
        db.flush()

        # 3️⃣ Criar itens
        for item in data.items:
            product = (
                db.query(Product)
                .filter(
                    Product.id == item.product_id,
                    Product.is_deleted.is_(False),
                )
                .first()
            )

            if not product:
                raise ProductNotFoundException(item.product_id)

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
            )

            db.add(order_item)

        # 4️⃣ Audit
        AuditService.log(
            db=db,
            action="order:create",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=(
                f"Order {order.id} created by {current_user.username}"
            ),
        )

        db.refresh(order)
        return order

    @staticmethod
    def assign_next_order(
            db: Session,
            *,
            current_user,
    ) -> Order:

        # 1️⃣ já tem pedido em produção?
        current_order = get_user_current_order(
            db,
            user_id=current_user.id,
        )

        if current_order:
            return current_order

        stmt = (
            select(Order)
            .where(
                Order.status == OrderStatus.AWAITING,
                Order.scheduled_date == date.today(),
                Order.is_deleted.is_(False),
            )
            .order_by(
                Order.priority.asc(),
                Order.created_at.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        order = db.execute(stmt).scalars().first()

        if not order:
            raise NoOrderAvailableException()

        # 2️⃣ marcar pedido
        order.status = OrderStatus.PRODUCING
        order.assigned_user_id = current_user.id

        # 3️⃣ criar WorkOrder (INÍCIO DO PEDIDO)
        work_order = WorkOrder(
            order_id=order.id,
            user_id=current_user.id,
            started_at=utcnow(),
        )
        db.add(work_order)

        # 4️⃣ definir primeiro item (APENAS ESTADO)
        first_item = resolve_current_item(order)
        if first_item:
            first_item.status = OrderItemStatus.PRODUCING

            # 🚀 iniciar WorkItem aqui (INÍCIO DO ITEM)
            work_item = WorkItem(
                order_id=order.id,
                product_id=first_item.product_id,
                user_id=current_user.id,
                order_item_id=first_item.id,
                started_at=utcnow(),
            )
            db.add(work_item)

        # 5️⃣ audit
        AuditService.log(
            db=db,
            action="order:assign",
            entity="order",
            entity_id=order.id,
            user_id=current_user.id,
            description=f"Order {order.id} assigned to {current_user.username}",
        )

        db.refresh(order)
        return order
