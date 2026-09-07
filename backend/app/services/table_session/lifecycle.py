"""TableSession lifecycle (U6/E) — session start + close-with-migration.

DB session injection (plan Q1=B): the frozen facade signatures carry no `db` param, so these
functions open their own Session via `_open_session()` (referencing app.db.SessionLocal through
the module so tests can monkeypatch it). `expire_on_commit=False` keeps the returned detached
TableSession's scalar attributes (`.id`, ...) readable by callers (U4/C) after commit/close.

Close notification (plan Q5=A): after commit, publish one `order_deleted` per migrated order
using the existing broker event types (no contract change). A not-yet-wired broker
(NotImplementedError) is tolerated so U6 runs standalone before U5/D merges.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app import db as _db
from app.errors import AppError, ErrorCode
from app.models import Order, TableSession
from app.repositories.order_history import OrderHistoryRepoImpl
from app.services import order_event_broker
from app.services.table_session import CloseResult


def _open_session() -> Session:
    s = _db.SessionLocal()
    s.expire_on_commit = False  # keep attributes on detached instances after commit
    return s


def get_or_start_active_session(table_id: int) -> TableSession:
    """Return the table's active session, starting a new one if none. Invariant: <=1 active (US-A-11)."""
    db = _open_session()
    try:
        session = (
            db.query(TableSession)
            .filter(TableSession.table_id == table_id, TableSession.status == "active")
            .first()
        )
        if session is None:
            session = TableSession(table_id=table_id, status="active", started_at=datetime.utcnow())
            db.add(session)
            db.commit()
        return session
    finally:
        db.close()


def close_table(table_id: int, actor: object = None) -> CloseResult:
    """Close usage: migrate the active session's orders to history + reset, in one transaction (US-A-12)."""
    closed_at = datetime.utcnow()
    db = _open_session()
    try:
        session = (
            db.query(TableSession)
            .filter(TableSession.table_id == table_id, TableSession.status == "active")
            .first()
        )
        if session is None:
            raise AppError(ErrorCode.CONFLICT, "활성 세션이 없습니다.", {"table_id": table_id})

        order_ids = [
            oid for (oid,) in db.query(Order.id).filter(Order.session_id == session.id).all()
        ]
        moved = OrderHistoryRepoImpl(db).move_session_orders(session.id, closed_at)
        session.status = "closed"
        session.closed_at = closed_at
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # After commit: notify the live dashboard that these orders are gone (Q5=A).
    for oid in order_ids:
        try:
            order_event_broker.broker.publish(
                order_event_broker.OrderEvent(type="order_deleted", payload={"order_id": oid})
            )
        except NotImplementedError:
            pass  # broker not wired yet (U5/D not merged); close still succeeds

    return CloseResult(moved_order_count=moved, closed_at=closed_at)
