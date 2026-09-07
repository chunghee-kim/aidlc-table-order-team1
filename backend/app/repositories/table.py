"""TableRepo (U2/A). Interface frozen in Phase 0; concrete SQLAlchemy impl added by U2/A."""
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Table


class TableRepo(Protocol):
    def find_by_number(self, store_id: int, table_number: int) -> Table | None: ...

    def upsert(self, table: Table) -> Table: ...


class SqlTableRepo:
    """Session-scoped concrete TableRepo. Caller owns commit/rollback."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_number(self, store_id: int, table_number: int) -> Table | None:
        return self.db.query(Table).filter_by(store_id=store_id, table_number=table_number).one_or_none()

    def find_by_id(self, table_id: int) -> Table | None:
        return self.db.get(Table, table_id)

    def upsert(self, table: Table) -> Table:
        # Add is idempotent for an already-persistent instance; flush assigns the PK for new rows.
        self.db.add(table)
        self.db.flush()
        return table
