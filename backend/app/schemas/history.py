"""Order history schemas (U6/E consumes; frozen in Phase 0)."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import OrderItemView


class OrderHistoryView(BaseModel):
    order_number: str
    items: list[OrderItemView]
    total_amount: int
    ordered_at: datetime
    closed_at: datetime
