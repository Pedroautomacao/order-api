from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.orders.enums import OrderStatus
from app.orders.models.order import Order


class OrderAdminService:
    """Ações administrativas sobre pedidos: priorizar e remarcar data."""

    @staticmethod
    def prioritize(db: Session, *, order: Order, current_user) -> Order:
        if order.status in (OrderStatus.CANCELED, OrderStatus.BILLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível priorizar um pedido cancelado ou faturado.",
            )
        if order.priority == "A":
            return order  # já priorizado

        with atomic(db):
            order.priority = "A"

            AuditService.log(
                db=db,
                action="order:set_priority",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=f"Pedido #{order.id} priorizado (prioridade A)",
            )

        db.refresh(order)
        return order

    @staticmethod
    def reschedule(db: Session, *, order: Order, new_date: date, current_user) -> Order:
        if order.status != OrderStatus.AWAITING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível remarcar a data de pedidos em Aguardando.",
            )
        if new_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova data não pode estar no passado.",
            )

        old = order.scheduled_date

        with atomic(db):
            order.scheduled_date = new_date

            AuditService.log(
                db=db,
                action="order:reschedule",
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=(
                    f"Entrega do pedido #{order.id} remarcada de "
                    f"{old.strftime('%d/%m/%Y')} para {new_date.strftime('%d/%m/%Y')}"
                ),
            )

        db.refresh(order)
        return order
