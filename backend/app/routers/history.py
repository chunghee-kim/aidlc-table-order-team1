"""HistoryRouter — U6/E. GET /api/admin/history?table=&date_from=&date_to= (admin, US-A-13/14)."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from app.auth.dependency import AdminContext, get_current_admin
from app.errors import AppError, ErrorCode
from app.schemas.history import OrderHistoryView
from app.services.history_service import list_history

router = APIRouter(prefix="/api/admin", tags=["history"])

# Filter dates are interpreted at store-local midnight (KST = UTC+9); stored timestamps are UTC.
_KST_OFFSET = timedelta(hours=9)


def _parse_date(value: str, field: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"잘못된 날짜 형식입니다: {field} (YYYY-MM-DD)",
            {field: value},
        ) from exc


def _date_range(date_from: str | None, date_to: str | None) -> tuple | None:
    """(start_inclusive, end_exclusive) in UTC, or None. Each bound derived from a KST-local day."""
    if not date_from and not date_to:
        return None
    start = _parse_date(date_from, "date_from") - _KST_OFFSET if date_from else None
    end = (_parse_date(date_to, "date_to") + timedelta(days=1)) - _KST_OFFSET if date_to else None
    return (start, end)


@router.get("/history", response_model=list[OrderHistoryView])
def history_endpoint(
    table: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    actor: AdminContext = Depends(get_current_admin),
) -> list[OrderHistoryView]:
    """Past order history for the admin's store, newest first (US-A-13), optional table/date filter (US-A-14)."""
    return list_history(actor.store_id, table, _date_range(date_from, date_to))
