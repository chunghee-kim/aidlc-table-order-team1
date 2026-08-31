"""U6 PBT — P2: close_table migrates losslessly + resets (US-A-12)."""
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import func
from support import add_order, new_memory_db

from app import db as appdb
from app.models import Order, OrderHistory, TableSession
from app.services.table_session import lifecycle

# An order = list of (unit_price, quantity); a session = list of orders (possibly empty).
_order = st.lists(
    st.tuples(st.integers(min_value=1, max_value=5000), st.integers(min_value=1, max_value=9)),
    min_size=1,
    max_size=4,
)
_session = st.lists(_order, min_size=0, max_size=6)


@settings(max_examples=50, deadline=None)
@given(orders=_session)
def test_p2_lossless_migration_and_reset(orders):
    new_memory_db()
    table_id = 1

    session = lifecycle.get_or_start_active_session(table_id)
    session_id = session.id

    expected_total = 0
    for i, items in enumerate(orders):
        expected_total += add_order(session_id, table_id, f"ORD-{i:05d}", items)

    result = lifecycle.close_table(table_id)

    # Lossless: moved count == number of orders.
    assert result.moved_order_count == len(orders)

    db = appdb.SessionLocal()
    try:
        # Originals physically removed.
        assert db.query(Order).filter(Order.session_id == session_id).count() == 0
        # History preserves every order and the exact totals.
        history = db.query(OrderHistory).filter(OrderHistory.session_id == session_id).all()
        assert len(history) == len(orders)
        assert sum(h.total_amount for h in history) == expected_total
        # items_snapshot sums match per-order totals.
        for h in history:
            snap_total = sum(it["unit_price"] * it["quantity"] for it in h.items_snapshot)
            assert snap_total == h.total_amount
        # Reset: no active session, table total is 0.
        assert (
            db.query(TableSession)
            .filter(TableSession.table_id == table_id, TableSession.status == "active")
            .count()
            == 0
        )
        remaining = (
            db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.table_id == table_id)
            .scalar()
        )
        assert remaining == 0
    finally:
        db.close()


def test_close_without_active_session_conflicts():
    from app.errors import AppError, ErrorCode

    new_memory_db()
    try:
        lifecycle.close_table(999)
    except AppError as exc:
        assert exc.code == ErrorCode.CONFLICT
    else:
        raise AssertionError("expected AppError(CONFLICT) when no active session")
