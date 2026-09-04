from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.core.time import utcnow
from app.database.atomic import atomic
from app.order_item_breaks.models import OrderItemBreak
from app.orders.dependencies import get_order_item_or_404
from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.exception_handler import OrderNotAssignedToUserException, InvalidOrderItemStateException, \
    InvalidProducedQuantityException, OrderItemNotFoundException, OrderNotInProductionException
from app.orders.models.order_item import OrderItem
from app.orders.models.work_item import WorkItem
from app.orders.repositories.work_item_repository import find_open_work_item
from app.orders.utils.resolve_current_item import resolve_current_item


class OrderItemService:
    @staticmethod
    def confirm_item(
            db: Session,
            *,
            order_item_id: int,
            data,
            current_user,
    ):
        # Trava a linha do item: sem isso duas confirmações simultâneas do
        # mesmo item passavam as duas pela guarda de status abaixo e cada uma
        # abria um WorkItem para o próximo item, deixando um aberto para sempre.
        item = (
            db.query(OrderItem)
            .filter(
                OrderItem.id == order_item_id,
                OrderItem.is_deleted.is_(False),
            )
            .with_for_update()
            .first()
        )
        if not item:
            raise OrderItemNotFoundException(order_item_id)

        order = item.order

        if order.assigned_user_id != current_user.id:
            raise OrderNotAssignedToUserException()

        if item.status != OrderItemStatus.PRODUCING:
            raise InvalidOrderItemStateException(
                item.id,
                OrderItemStatus.PRODUCING,
                item.status,
            )

        if data.produced_quantity is None or data.produced_quantity <= 0:
            raise InvalidProducedQuantityException()

        expected = item.quantity

        with atomic(db):
            if data.produced_quantity < expected:
                db.add(
                    OrderItemBreak(
                        id=uuid4(),
                        order_id=item.order_id,
                        order_item_id=item.id,
                        expected_quantity=expected,
                        confirmed_quantity=data.produced_quantity,
                        difference_quantity=expected - data.produced_quantity,
                        created_by=current_user.id,
                    )
                )

            # salvar quantidade produzida
            item.produced_quantity = data.produced_quantity
            item.status = OrderItemStatus.PRODUCED

            # fechar work_item aberto. Itens que entraram em produção antes
            # do apontamento existir não têm um; antes disso o serviço
            # estourava e o pedido ficava travado (nem confirma, nem finaliza).
            work_item = find_open_work_item(db, order_item_id=item.id)
            if work_item is not None:
                work_item.ended_at = utcnow()
                work_item.time_to_produced_secs = int(
                    (work_item.ended_at - work_item.started_at).total_seconds()
                )

            # iniciar próximo item
            next_item = resolve_current_item(order)
            if next_item:
                next_item.status = OrderItemStatus.PRODUCING

                db.add(
                    WorkItem(
                        order_id=order.id,
                        product_id=next_item.product_id,
                        user_id=current_user.id,
                        started_at=utcnow(),
                        order_item_id=next_item.id
                    )
                )

            AuditService.log(
                db=db,
                action="order:item_confirm",
                entity="order_item",
                entity_id=item.id,
                user_id=current_user.id,
                description=f"Produced {data.produced_quantity}",
            )

        return order

    @staticmethod
    def update_produced_quantity(
            db: Session,
            *,
            order_item_id: int,
            data,
            current_user,
    ):
        item = get_order_item_or_404(db, order_item_id)
        order = item.order

        if order.assigned_user_id != current_user.id:
            raise OrderNotAssignedToUserException()

        # O finish não limpa assigned_user_id, então sem esta guarda o produtor
        # alterava a quantidade produzida de um pedido já finalizado ou já
        # faturado — o fiscal emitia nota sobre um número que ainda mudava.
        if order.status != OrderStatus.PRODUCING:
            raise OrderNotInProductionException()

        if item.status != OrderItemStatus.PRODUCED:
            raise InvalidOrderItemStateException(
                item.id,
                OrderItemStatus.PRODUCED,
                item.status,
            )

        old_qty = item.produced_quantity
        new_qty = data.produced_quantity

        if new_qty is None or new_qty <= 0:
            raise InvalidProducedQuantityException()

        with atomic(db):
            # Anula a quebra vigente e recria se necessário. Delete físico sem
            # filtro destruía também as quebras que o reset apenas anulou,
            # apagando o histórico dos ciclos anteriores.
            (
                db.query(OrderItemBreak)
                .filter(
                    OrderItemBreak.order_item_id == item.id,
                    OrderItemBreak.is_deleted.is_(False),
                )
                .update(
                    {OrderItemBreak.is_deleted: True},
                    synchronize_session=False,
                )
            )

            if new_qty < item.quantity:
                db.add(
                    OrderItemBreak(
                        id=uuid4(),
                        order_id=item.order_id,
                        order_item_id=item.id,
                        expected_quantity=item.quantity,
                        confirmed_quantity=new_qty,
                        difference_quantity=item.quantity - new_qty,
                        created_by=current_user.id,
                    )
                )

            item.produced_quantity = new_qty

            AuditService.log(
                db=db,
                action="order:item_update_quantity",
                entity="order_item",
                entity_id=item.id,
                user_id=current_user.id,
                description=f"Updated produced qty from {old_qty} to {new_qty}",
            )

        return order
