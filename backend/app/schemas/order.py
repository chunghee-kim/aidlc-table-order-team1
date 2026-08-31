"""Customer order schemas (U4/C consumes; frozen in Phase 0)."""
from pydantic import BaseModel

from app.schemas.common import OrderView


class OrderItemInput(BaseModel):
    menu_id: int
    quantity: int


class CreateOrderRequest(BaseModel):
    store_id: int
    table_id: int
    items: list[OrderItemInput]


class OrderPage(BaseModel):
    items: list[OrderView]
    next_cursor: int | None = None
