from datetime import datetime
from typing import Protocol

from app.models import TableSession


class SessionRepo(Protocol):
    def find_active_by_table(self, table_id: int) -> TableSession | None: ...

    def create(self, table_id: int) -> TableSession: ...

    def close(self, session_id: int, closed_at: datetime) -> None: ...
