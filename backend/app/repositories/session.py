"""SessionRepo (U2/A owns file; identification part). Interface frozen in Phase 0.

Concrete impl provided here so U6/E lifecycle can consume it. U2 itself does not start
sessions (session lifecycle is U6); it only identifies store/table (see identify.py).
"""
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import TableSession


class SessionRepo(Protocol):
    def find_active_by_table(self, table_id: int) -> TableSession | None: ...

    def create(self, table_id: int) -> TableSession: ...

    def close(self, session_id: int, closed_at: datetime) -> None: ...


class SqlSessionRepo:
    """Session-scoped concrete SessionRepo. Caller owns commit/rollback."""

    def __init__(self, db: Session):
        self.db = db

    def find_active_by_table(self, table_id: int) -> TableSession | None:
        return (
            self.db.query(TableSession)
            .filter_by(table_id=table_id, status="active")
            .order_by(TableSession.started_at.desc())
            .first()
        )

    def create(self, table_id: int) -> TableSession:
        session = TableSession(table_id=table_id, status="active")
        self.db.add(session)
        self.db.flush()
        return session

    def close(self, session_id: int, closed_at: datetime) -> None:
        session = self.db.get(TableSession, session_id)
        if session is not None:
            session.status = "closed"
            session.closed_at = closed_at
