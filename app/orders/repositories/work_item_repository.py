from sqlalchemy.orm import Session

from app.orders.models.work_item import WorkItem
from app.orders.exception_handler import WorkItemNotFoundException


def get_open_work_item(
    db: Session,
    *,
    order_id: int,
    product_id: int,
    user_id: int,
) -> WorkItem:
    work_item = (
        db.query(WorkItem)
        .filter(
            WorkItem.order_id == order_id,
            WorkItem.product_id == product_id,
            WorkItem.user_id == user_id,
            WorkItem.ended_at.is_(None),
            WorkItem.is_deleted.is_(False),
        )
        .first()
    )

    if not work_item:
        raise WorkItemNotFoundException()

    return work_item
