from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.audit.services.audit_service import AuditService
from app.core.time import as_utc, utcnow
from app.database.atomic import atomic
from app.order_item_breaks.models import OrderItemBreak
from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.orders.models.work_item import WorkItem
from app.orders.models.work_order import WorkOrder


class OrderCancelService:
    @staticmethod
    def cancel(
        *,
        db: Session,
        order: Order,
        current_user,
        is_admin: bool,
    ) -> Order:
        if order.status == OrderStatus.BILLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pedidos faturados não podem ser cancelados.",
            )

        if order.status == OrderStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pedido já está cancelado.",
            )

        if not is_admin and order.status == OrderStatus.PRODUCING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order in production cannot be canceled by creator.",
            )

        with atomic(db):
            order.status = OrderStatus.CANCELED
            order.assigned_user_id = None

            # O apontamento aberto é ENCERRADO, não apagado: o pedido fica
            # parado com o que já havia sido produzido no instante do
            # cancelamento, e o tempo trabalhado até ali não se perde. Apagar
            # resolvia o ciclo que nunca terminava, mas junto levava a
            # informação que o produtor tinha registrado.
            agora = utcnow()
            for model in (WorkOrder, WorkItem):
                abertos = (
                    db.query(model)
                    .filter(
                        model.order_id == order.id,
                        model.ended_at.is_(None),
                        model.is_deleted.is_(False),
                    )
                    .all()
                )
                for apontamento in abertos:
                    apontamento.ended_at = agora
                    apontamento.time_to_produced_secs = int(
                        (
                            as_utc(agora) - as_utc(apontamento.started_at)
                        ).total_seconds()
                    )

            # O status dos itens e as quebras permanecem como estavam: é o
            # retrato do cancelamento, e o pedido cancelado não volta para a
            # fila, então item em Producing não sustenta ciclo nenhum.

            AuditService.log(
                db=db,
                action="order:cancel",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=f"Pedido #{order.id} cancelado",
            )

        db.refresh(order)
        return order
