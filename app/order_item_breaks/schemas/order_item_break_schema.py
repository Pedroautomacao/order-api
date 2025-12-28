from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class OrderItemBreakResponse(BaseModel):
    id: UUID
    order_id: UUID
    order_item_id: UUID

    expected_quantity: Decimal
    confirmed_quantity: Decimal
    difference_quantity: Decimal

    created_at: datetime
    created_by: UUID | None

    class Config:
        from_attributes = True
