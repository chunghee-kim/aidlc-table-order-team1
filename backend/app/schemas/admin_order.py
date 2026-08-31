"""Admin order monitoring schemas (U5/D consumes; frozen in Phase 0)."""
from pydantic import BaseModel


class ChangeStatusRequest(BaseModel):
    status: str  # 대기중 | 준비중 | 완료


class TableTotals(BaseModel):
    table_id: int
    total_amount: int
