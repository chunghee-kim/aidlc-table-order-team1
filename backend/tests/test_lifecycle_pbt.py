"""U6 PBT — P1: active session <= 1 and idempotent (US-A-11)."""
from hypothesis import given, settings
from hypothesis import strategies as st
from support import new_memory_db

from app import db as appdb
from app.models import TableSession
from app.services.table_session import lifecycle


@settings(max_examples=50, deadline=None)
@given(
    calls=st.integers(min_value=1, max_value=8),
    table_id=st.integers(min_value=1, max_value=5),
)
def test_p1_active_session_at_most_one_and_idempotent(calls, table_id):
    new_memory_db()

    returned_ids = set()
    for _ in range(calls):
        session = lifecycle.get_or_start_active_session(table_id)
        returned_ids.add(session.id)

    db = appdb.SessionLocal()
    try:
        active_count = (
            db.query(TableSession)
            .filter(TableSession.table_id == table_id, TableSession.status == "active")
            .count()
        )
    finally:
        db.close()

    # Invariant: at most one active session per table; every call returns the same session.
    assert active_count == 1
    assert len(returned_ids) == 1


@settings(max_examples=25, deadline=None)
@given(table_ids=st.lists(st.integers(min_value=1, max_value=6), min_size=1, max_size=6))
def test_p1_independent_per_table(table_ids):
    new_memory_db()
    for tid in table_ids:
        lifecycle.get_or_start_active_session(tid)

    db = appdb.SessionLocal()
    try:
        for tid in set(table_ids):
            active = (
                db.query(TableSession)
                .filter(TableSession.table_id == tid, TableSession.status == "active")
                .count()
            )
            assert active == 1
    finally:
        db.close()
