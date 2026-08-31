"""OrderRouter (U4/C) — customer order endpoints, table-session scoped (no admin JWT).

  POST /api/orders          -> OrderService.create_order   (empty cart blocked; US-C-12/13)
  GET  /api/orders?session_id=&cursor=&limit=  -> list_current_session_orders (US-C-14)

Session identity is carried in the request (store_id/table_id from TableSessionContext);
the session itself is ensured by U6/E via the frozen create_order contract.
"""
from fastapi import APIRouter, Query

from app.schemas.common import OrderView, PageParams
from app.schemas.order import CreateOrderRequest, OrderPage
from app.services import order as order_service
from app.services.table_session import TableSessionContext

router = APIRouter(prefix="/api/orders", tags=["order"])


@router.post("", response_model=OrderView, status_code=201)
def create_order(req: CreateOrderRequest) -> OrderView:
    ctx = TableSessionContext(store_id=req.store_id, table_id=req.table_id, session_id=None)
    return order_service.create_order(ctx, req.items)


@router.get("", response_model=OrderPage)
def list_current_orders(
    session_id: int = Query(..., description="현재 테이블 세션 ID"),
    cursor: int | None = Query(None, description="이전 페이지 마지막 주문 ID(무한 스크롤)"),
    limit: int = Query(20, ge=1, le=100),
) -> OrderPage:
    return order_service.list_current_session_orders(session_id, PageParams(cursor=cursor, limit=limit))
