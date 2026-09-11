from fastapi import HTTPException, status

from app.audit.services.audit_service import AuditService
from app.core.time import as_utc, utcnow
from app.database.atomic import atomic
from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.exception_handler import OrderNotFinishedException
from app.orders.models.work_order import WorkOrder


class OrderFinishService:
    @staticmethod
    def finish_order(
        db,
        *,
        order,
        current_user,
    ):

        if order.status != OrderStatus.PRODUCING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas pedidos em produção podem ser finalizados.",
            )

        # any() sobre lista vazia e False: sem esta guarda um pedido sem
        # itens era finalizado e marcado como Produzido.
        if not order.items:
            raise OrderNotFinishedException()

        if any(i.status != OrderItemStatus.PRODUCED for i in order.items):
            raise OrderNotFinishedException()

        work_order = OrderFinishService._get_open_work_order(db, order=order)

        with atomic(db):
            order.status = OrderStatus.PRODUCED

            # Pedidos que entraram em produção antes da WorkOrder existir não têm
            # registro aberto — finaliza sem apontamento de tempo em vez de quebrar.
            if work_order is not None:
                work_order.ended_at = utcnow()
                # as_utc nos dois lados: o relógio pode vir naive (SQLite dos
                # testes) ou aware (Postgres), e misturar os dois estoura
                work_order.time_to_produced_secs = int(
                    (
                        as_utc(work_order.ended_at) - as_utc(work_order.started_at)
                    ).total_seconds()
                )

            AuditService.log(
                db=db,
                action="order:finish",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=(
                    f"Produção do pedido #{order.id} finalizada "
                    f"({len(order.items)} item(ns))"
                ),
            )

        db.refresh(order)
        return order

    @staticmethod
    def _get_open_work_order(db, *, order) -> WorkOrder | None:
        """WorkOrder aberta mais recente do pedido."""
        return (
            db.query(WorkOrder)
            .filter(
                WorkOrder.order_id == order.id,
                WorkOrder.ended_at.is_(None),
                WorkOrder.is_deleted.is_(False),
            )
            .order_by(WorkOrder.started_at.desc())
            .first()
        )
