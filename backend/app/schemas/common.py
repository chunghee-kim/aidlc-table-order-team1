"""Common response schemas shared across endpoints (Phase 0 freeze)."""
from datetime import datetime

from pydantic import BaseModel


class OrderItemView(BaseModel):
    menu_name: str
    unit_price: int
    quantity: int


class OrderView(BaseModel):
    """Common order projection (application-design.md §3)."""

    order_number: str
    table_id: int
    session_id: int
    items: list[OrderItemView]
    total_amount: int
    status: str  # 대기중 | 준비중 | 완료
    created_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorBody(BaseModel):
    """Structured error body: {"error": {code, message, details}}."""

    error: ErrorDetail


class PageParams(BaseModel):
    cursor: int | None = None
    limit: int = 20
