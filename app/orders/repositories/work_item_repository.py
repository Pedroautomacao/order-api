from sqlalchemy.orm import Session

from app.orders.models.work_item import WorkItem


def find_open_work_item(
    db: Session,
    *,
    order_item_id: int,
) -> WorkItem | None:
    """Apontamento aberto mais recente do item, ou None.

    Identifica pelo próprio ``order_item_id``, que sempre existe — casar por
    produto + usuário confundia itens do mesmo produto no mesmo pedido.
    """
    return (
        db.query(WorkItem)
        .filter(
            WorkItem.order_item_id == order_item_id,
            WorkItem.ended_at.is_(None),
            WorkItem.is_deleted.is_(False),
        )
        .order_by(WorkItem.started_at.desc())
        .first()
    )
