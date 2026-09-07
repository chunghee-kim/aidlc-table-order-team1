"""AdminOrderRouter (U5/D) — order monitoring dashboard: snapshot, SSE stream, status, delete.

  GET    /api/admin/orders[?table=n]      -> list[AdminOrderView]        (US-A-05/08)
  GET    /api/admin/orders/stream?token=  -> text/event-stream           (US-A-06)
  PATCH  /api/admin/orders/{id}/status    -> OrderView                   (US-A-09)
  DELETE /api/admin/orders/{id}           -> TableTotals                 (US-A-10)

Auth: admin JWT. REST endpoints use the `get_current_admin` header dependency; the SSE stream
takes the token as a query param (EventSource cannot set headers, Q5-A) and verifies it the same way.
"""
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.auth.dependency import AdminContext, get_current_admin, verify_token
from app.schemas.admin_order import AdminOrderView, ChangeStatusRequest, TableTotals
from app.schemas.common import OrderView
from app.services import order as order_service
from app.services.order_event_broker import broker

router = APIRouter(prefix="/api/admin/orders", tags=["admin-order"])


@router.get("", response_model=list[AdminOrderView])
def list_orders(
    admin: AdminContext = Depends(get_current_admin),
    table: int | None = Query(None, description="테이블별 필터(초기 스냅샷)"),
) -> list[AdminOrderView]:
    return order_service.list_admin_orders_detailed(admin.store_id, table)


@router.get("/stream")
async def stream_orders(token: str = Query(..., description="관리자 JWT (EventSource 헤더 불가로 쿼리 전달)")):
    admin = verify_token(token)  # raises AppError(UNAUTHORIZED) on invalid/expired (BR-U5-13).

    async def event_source():
        async for frame in broker.subscribe(admin.store_id):
            yield f"data: {json.dumps(frame, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering so events flush immediately
        },
    )


@router.patch("/{order_id}/status", response_model=OrderView)
def change_status(
    order_id: int,
    req: ChangeStatusRequest,
    admin: AdminContext = Depends(get_current_admin),
) -> OrderView:
    return order_service.change_status(order_id, req.status, admin)


@router.delete("/{order_id}", response_model=TableTotals)
def delete_order(
    order_id: int,
    admin: AdminContext = Depends(get_current_admin),
) -> TableTotals:
    return order_service.delete_order(order_id, admin)
