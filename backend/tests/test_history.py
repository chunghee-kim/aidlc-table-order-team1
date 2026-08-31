"""U6 — HistoryService + router date-range parsing (US-A-13/14)."""
from datetime import datetime, timedelta

import pytest
from support import new_memory_db, seed_store, seed_table

from app import db as appdb
from app.errors import AppError
from app.models import OrderHistory
from app.routers.history import _date_range
from app.services.history_service import list_history


def _add_history(table_id, session_id, order_number, items, total, ordered_at, closed_at):
    db = appdb.SessionLocal()
    try:
        db.add(
            OrderHistory(
                table_id=table_id,
                session_id=session_id,
                order_number=order_number,
                items_snapshot=items,
                total_amount=total,
                ordered_at=ordered_at,
                closed_at=closed_at,
            )
        )
        db.commit()
    finally:
        db.close()


def test_list_history_store_scoped_and_newest_first():
    new_memory_db()
    seed_store(1)
    seed_store(2)
    seed_table(1, store_id=1)
    seed_table(2, store_id=2)
    t = datetime(2026, 8, 30, 12, 0, 0)
    _add_history(1, 10, "A", [{"menu_name": "m", "unit_price": 100, "quantity": 2}], 200, t, t)
    _add_history(1, 11, "B", [{"menu_name": "m", "unit_price": 50, "quantity": 1}], 50, t, t + timedelta(hours=1))
    _add_history(2, 12, "C", [{"menu_name": "m", "unit_price": 10, "quantity": 1}], 10, t, t)

    res = list_history(1, None, None)

    assert [h.order_number for h in res] == ["B", "A"]  # newest closed_at first
    assert all(h.order_number != "C" for h in res)  # store 2 excluded
    assert res[1].items[0].unit_price == 100  # items_snapshot -> OrderItemView


def test_list_history_table_filter():
    new_memory_db()
    seed_store(1)
    seed_table(1, store_id=1)
    seed_table(2, store_id=1)
    t = datetime(2026, 8, 30, 12, 0, 0)
    _add_history(1, 10, "T1", [{"menu_name": "m", "unit_price": 100, "quantity": 1}], 100, t, t)
    _add_history(2, 11, "T2", [{"menu_name": "m", "unit_price": 100, "quantity": 1}], 100, t, t)

    res = list_history(1, 2, None)
    assert [h.order_number for h in res] == ["T2"]


def test_list_history_date_filter_uses_kst_boundaries():
    new_memory_db()
    seed_store(1)
    seed_table(1, store_id=1)
    # KST day 2026-08-31 == UTC [2026-08-30 15:00, 2026-08-31 15:00)
    inside = datetime(2026, 8, 30, 16, 0, 0)  # 2026-08-31 01:00 KST
    outside = datetime(2026, 8, 30, 14, 0, 0)  # 2026-08-30 23:00 KST
    _add_history(1, 10, "IN", [{"menu_name": "m", "unit_price": 1, "quantity": 1}], 1, inside, inside)
    _add_history(1, 11, "OUT", [{"menu_name": "m", "unit_price": 1, "quantity": 1}], 1, outside, outside)

    res = list_history(1, None, _date_range("2026-08-31", "2026-08-31"))
    assert [h.order_number for h in res] == ["IN"]


def test_date_range_none_and_invalid():
    assert _date_range(None, None) is None
    with pytest.raises(AppError):
        _date_range("2026-13-40", None)


def test_date_range_kst_conversion():
    start, end = _date_range("2026-08-31", "2026-08-31")
    assert start == datetime(2026, 8, 30, 15, 0, 0)
    assert end == datetime(2026, 8, 31, 15, 0, 0)
