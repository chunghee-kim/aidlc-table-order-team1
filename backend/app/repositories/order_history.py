"""OrderHistoryRepo (U6/E owns Protocol + concrete impl).

Self-contained snapshot access. `move_session_orders` migrates a session's orders into
OrderHistory losslessly (snapshot insert + physical delete of the originals) inside the
caller's transaction; `list` reads history scoped to a store (join via non-FK table_id).
"""
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, OrderHistory, Table


class OrderHistoryRepo(Protocol):
    def move_session_orders(self, session_id: int, closed_at: datetime) -> int:
        """Migrate a session's orders to history; returns migrated count (lossless)."""
        ...

    def list(
        self, store_id: int, table_filter: int | None, date_range: tuple | None
    ) -> list[OrderHistory]: ...


class OrderHistoryRepoImpl:
    """Concrete OrderHistoryRepo bound to a request/transaction-scoped Session."""

    def __init__(self, db: Session):
        self.db = db

    def move_session_orders(self, session_id: int, closed_at: datetime) -> int:
        """Snapshot each order of the session into OrderHistory, then delete the originals.

        Runs within the caller's transaction (no commit here). OrderItem rows are removed by
        the Order.items cascade when the Order is deleted. Returns the number moved.
        """
        orders = self.db.query(Order).filter(Order.session_id == session_id).all()
        moved = 0
        for order in orders:
            items_snapshot = [
                {"menu_name": it.menu_name, "unit_price": it.unit_price, "quantity": it.quantity}
                for it in order.items
            ]
            self.db.add(
                OrderHistory(
                    table_id=order.table_id,
                    session_id=session_id,
                    order_number=order.order_number,
                    items_snapshot=items_snapshot,
                    total_amount=order.total_amount,
                    ordered_at=order.created_at,
                    closed_at=closed_at,
                )
            )
            self.db.delete(order)  # cascade="all, delete-orphan" removes OrderItem rows
            moved += 1
        self.db.flush()
        return moved

    def list(
        self, store_id: int, table_filter: int | None, date_range: tuple | None
    ) -> list[OrderHistory]:
        """History for a store, newest first. date_range = (start_inclusive, end_exclusive), each nullable."""
        stmt = (
            select(OrderHistory)
            .join(Table, Table.id == OrderHistory.table_id)
            .where(Table.store_id == store_id)
        )
        if table_filter is not None:
            stmt = stmt.where(OrderHistory.table_id == table_filter)
        if date_range is not None:
            start, end = date_range
            if start is not None:
                stmt = stmt.where(OrderHistory.closed_at >= start)
            if end is not None:
                stmt = stmt.where(OrderHistory.closed_at < end)
        stmt = stmt.order_by(OrderHistory.closed_at.desc(), OrderHistory.id.desc())
        return list(self.db.execute(stmt).scalars().all())
