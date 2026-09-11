from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.exception_handler import ClientNotFoundException
from app.core.time import min_scheduled_date, today_sp, utcnow
from app.database.atomic import atomic
from app.orders.exception_handler import DuplicateProductInOrderException, InvalidScheduledDateException, \
    DuplicateOrderForClientException, NoOrderAvailableException
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.enums import OrderStatus, ProductionApproval, OrderItemStatus
from app.clients.models.client import Client
from app.orders.models.work_item import WorkItem
from app.orders.models.work_order import WorkOrder
from app.orders.repositories.order_repository import get_user_current_order
from app.products.exception_handler import ProductNotFoundException
from app.products.models.product import Product
from app.audit.services.audit_service import AuditService
from app.users.models.user import User
from app.orders.utils.resolve_current_item import resolve_current_item


class OrderService:
    @staticmethod
    def create(
        db: Session,
        *,
        data,
        current_user: User,
    ) -> Order:
        if not data.items:
            raise ValueError("Order must have at least one item")

        # 0️⃣ validar scheduled date — hoje vale até as 16h de São Paulo
        minima = min_scheduled_date()
        if data.scheduled_date < minima:
            raise InvalidScheduledDateException(data.scheduled_date, minima)

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

        # 1.5️⃣ forma de pagamento + validação de crédito
        from decimal import Decimal
        from app.orders.enums import PaymentMethod
        from app.orders.services.credit_service import CreditService

        payment_method = getattr(data, "payment_method", None) or PaymentMethod.CASH
        if not isinstance(payment_method, PaymentMethod):
            payment_method = PaymentMethod(payment_method)

        CreditService.validate_payment_method(client, payment_method)

        # calcular total do pedido (Σ preço × qtd) e validar limite se a prazo
        total_amount = CreditService.compute_order_amount(db, data.items)
        CreditService.check_credit_or_raise(
            db,
            client=client,
            payment_method=payment_method,
            order_amount=total_amount,
        )

        # 2️⃣ Criar order
        order = Order(
            client_id=client.id,
            created_by_user_id=current_user.id,
            priority=client.priority,
            status=OrderStatus.AWAITING,
            scheduled_date=data.scheduled_date,
            payment_method=payment_method,
            is_paid=False,
            total_amount=total_amount,
        )

        with atomic(db):
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
                    # congela o preço: o do item quando informado, senão o de
                    # tabela do produto neste instante
                    unit_price=(
                        item.unit_price
                        if getattr(item, "unit_price", None) is not None
                        else (product.unit_price or 0)
                    ),
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
                    f"Pedido #{order.id} criado para {client.name} "
                    f"com entrega em {data.scheduled_date.strftime('%d/%m/%Y')}"
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

        # 0️⃣ serializa por produtor: a checagem abaixo é uma leitura, então
        # duas chamadas simultâneas do mesmo usuário passavam as duas e ele
        # ficava com DOIS pedidos em produção.
        (
            db.query(User)
            .filter(User.id == current_user.id)
            .with_for_update()
            .first()
        )

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
                # só produz o que foi liberado: pedido aguardando aprovação ou
                # recusado nunca chega na fila do produtor
                Order.production_approval == ProductionApproval.APPROVED,
                Order.scheduled_date == today_sp(),
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

        # o SELECT ... FOR UPDATE acima segura a linha até o commit do bloco
        with atomic(db):
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
                description=f"Pedido #{order.id} atribuído à produção",
            )

        db.refresh(order)
        return order
