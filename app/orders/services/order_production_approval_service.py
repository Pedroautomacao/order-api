from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit.services.audit_service import AuditService
from app.database.atomic import atomic
from app.orders.enums import OrderStatus, ProductionApproval
from app.orders.models.order import Order


# Mesma regra de OrderAdminService.prioritize: pedido cancelado ou faturado
# está encerrado, mexer na liberação de produção não muda mais nada.
_ESTADOS_ENCERRADOS = (OrderStatus.CANCELED, OrderStatus.BILLED)

_ROTULO = {
    ProductionApproval.APPROVED: "aprovada",
    ProductionApproval.RECUSED: "recusada",
}


class OrderProductionApprovalService:
    """Libera ou barra a produção de um pedido.

    A decisão é reversível nos dois sentidos de propósito: aprovar por engano e
    recusar por engano são erros igualmente prováveis, e sem a volta o pedido
    ficaria travado.
    """

    @staticmethod
    def approve(db: Session, *, order: Order, current_user) -> Order:
        return OrderProductionApprovalService._decidir(
            db,
            order=order,
            novo=ProductionApproval.APPROVED,
            action="order:approve_production",
            current_user=current_user,
        )

    @staticmethod
    def recuse(db: Session, *, order: Order, current_user) -> Order:
        return OrderProductionApprovalService._decidir(
            db,
            order=order,
            novo=ProductionApproval.RECUSED,
            action="order:recuse_production",
            current_user=current_user,
        )

    @staticmethod
    def _decidir(
        db: Session,
        *,
        order: Order,
        novo: ProductionApproval,
        action: str,
        current_user,
    ) -> Order:
        if order.status in _ESTADOS_ENCERRADOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não é possível alterar a liberação de produção de um "
                    "pedido cancelado ou faturado."
                ),
            )

        anterior = order.production_approval

        if anterior == novo:
            return order  # nada a fazer, e sem registro de auditoria vazio

        with atomic(db):
            order.production_approval = novo

            AuditService.log(
                db=db,
                action=action,
                entity="order",
                entity_id=order.id,
                user_id=current_user.id,
                description=(
                    f"Produção do pedido #{order.id} {_ROTULO[novo]} "
                    f"(estava como {anterior.value})"
                ),
            )

        db.refresh(order)
        return order
