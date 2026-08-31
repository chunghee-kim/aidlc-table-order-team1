from typing import Protocol

from app.models import OrderHistory


class OrderHistoryRepo(Protocol):
    def move_session_orders(self, session_id: int) -> int:
        """Migrate a session's orders to history; returns migrated count (lossless)."""
        ...

    def list(self, store_id: int, table_filter: int | None, date_range: tuple | None) -> list[OrderHistory]: ...
