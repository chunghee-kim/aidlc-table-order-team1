"""Admin order monitoring schemas (U5/D consumes; frozen in Phase 0).

`AdminOrderView` is an additive U5/D projection: the frozen common `OrderView` carries no
`order_id`, but the monitoring dashboard keys every card/action by it (business-logic-model §6).
"""
from pydantic import BaseModel

from app.schemas.common import OrderView


class ChangeStatusRequest(BaseModel):
    status: str  # 대기중 | 준비중 | 완료


class TableTotals(BaseModel):
    table_id: int
    total_amount: int


class AdminOrderView(OrderView):
    """OrderView + persistent order id, for the admin monitoring snapshot/list (US-A-05)."""

    order_id: int
