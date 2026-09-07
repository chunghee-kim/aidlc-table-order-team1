"""HistoryService (U6/E) — past order history for the admin (US-A-13/14).

Read-only. Opens its own Session (plan Q1=B; referenced via app.db so tests can monkeypatch).
"""
from app import db as _db
from app.repositories.order_history import OrderHistoryRepoImpl
from app.schemas.common import OrderItemView
from app.schemas.history import OrderHistoryView


def list_history(
    store_id: int, table_filter: int | None = None, date_range: tuple | None = None
) -> list[OrderHistoryView]:
    """Closed sessions' orders for a store, newest first, optionally filtered by table/date range."""
    db = _db.SessionLocal()
    try:
        rows = OrderHistoryRepoImpl(db).list(store_id, table_filter, date_range)
        return [
            OrderHistoryView(
                order_number=r.order_number,
                items=[OrderItemView(**it) for it in r.items_snapshot],
                total_amount=r.total_amount,
                ordered_at=r.ordered_at,
                closed_at=r.closed_at,
            )
            for r in rows
        ]
    finally:
        db.close()
