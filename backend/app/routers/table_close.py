"""TableRouter (close) — U6/E. POST /api/admin/tables/{id}/close (admin)."""
from fastapi import APIRouter, Depends

from app.auth.dependency import AdminContext, get_current_admin
from app.schemas.table import CloseResponse
from app.services.table_session import close_table

router = APIRouter(prefix="/api/admin", tags=["table"])


@router.post("/tables/{table_id}/close", response_model=CloseResponse)
def close_table_endpoint(
    table_id: int, actor: AdminContext = Depends(get_current_admin)
) -> CloseResponse:
    """Close a table's active session: migrate orders to history losslessly + reset (US-A-12)."""
    result = close_table(table_id, actor)
    return CloseResponse(moved_order_count=result.moved_order_count, closed_at=result.closed_at)
