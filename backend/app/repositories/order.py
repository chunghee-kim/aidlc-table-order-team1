"""OrderRepo — data access for orders (U4/C owns this file).

The `OrderRepo` Protocol is the Phase 0 frozen contract. `SqlOrderRepo` is the concrete
SQLAlchemy implementation added by U4/C; it is session-scoped (holds a Session) and used by
both U4/C (create.py: create/list) and U5/D (admin.py: update_status/delete/sum) at integration.
Do NOT change the Protocol signatures without owner+consumer agreement.
"""
from typing import Protocol

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Table, TableSession


class OrderRepo(Protocol):
    def create(self, order: Order, items: list) -> Order: ...

    def list_by_session(self, session_id: int) -> list[Order]: ...

    def list_active_by_store(self, store_id: int, table_filter: int | None = None) -> list[Order]: ...

    def update_status(self, order_id: int, status: str) -> Order: ...

    def delete(self, order_id: int) -> None: ...

    def sum_total_by_table(self, table_id: int) -> int: ...


class SqlOrderRepo:
    """Concrete OrderRepo bound to a request/service-scoped SQLAlchemy Session.

    The service layer owns commit/rollback (see db.py); this repo only stages changes.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, order: Order, items: list[OrderItem]) -> Order:
        self.db.add(order)
        self.db.flush()  # assign order.id
        for item in items:
            item.order_id = order.id
            self.db.add(item)
        self.db.flush()
        return order

    def get(self, order_id: int) -> Order | None:
        return self.db.get(Order, order_id)

    def list_by_session(self, session_id: int) -> list[Order]:
        # Time order (US-C-14). Tie-break by id for stable cursor pagination.
        return (
            self.db.query(Order)
            .filter(Order.session_id == session_id)
            .order_by(Order.created_at.asc(), Order.id.asc())
            .all()
        )

    def list_by_session_page(self, session_id: int, cursor: int | None, limit: int) -> list[Order]:
        """Cursor pagination by ascending id. `cursor` is the last-seen order id (exclusive)."""
        q = self.db.query(Order).filter(Order.session_id == session_id)
        if cursor is not None:
            q = q.filter(Order.id > cursor)
        return q.order_by(Order.id.asc()).limit(limit).all()

    def list_active_by_store(self, store_id: int, table_filter: int | None = None) -> list[Order]:
        """Orders belonging to currently active sessions of a store (admin dashboard snapshot)."""
        q = (
            self.db.query(Order)
            .join(TableSession, Order.session_id == TableSession.id)
            .join(Table, Order.table_id == Table.id)
            .filter(Table.store_id == store_id, TableSession.status == "active")
        )
        if table_filter is not None:
            q = q.filter(Order.table_id == table_filter)
        return q.order_by(Order.created_at.asc(), Order.id.asc()).all()

    def update_status(self, order_id: int, status: str) -> Order:
        order = self.db.get(Order, order_id)
        if order is None:
            raise ValueError(f"order {order_id} not found")
        order.status = status
        self.db.flush()
        return order

    def delete(self, order_id: int) -> None:
        order = self.db.get(Order, order_id)
        if order is not None:
            self.db.delete(order)
            self.db.flush()

    def sum_total_by_table(self, table_id: int) -> int:
        """Total of orders under the table's active session (remaining sum)."""
        total = (
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .join(TableSession, Order.session_id == TableSession.id)
            .filter(Order.table_id == table_id, TableSession.status == "active")
            .scalar()
        )
        return int(total or 0)

    def max_order_number_today(self, store_id: int, prefix: str) -> str | None:
        """Largest order_number for this store on the given YYYYMMDD prefix (for daily sequencing)."""
        row = (
            self.db.query(Order.order_number)
            .join(Table, Order.table_id == Table.id)
            .filter(Table.store_id == store_id, Order.order_number.like(f"{prefix}-%"))
            .order_by(Order.order_number.desc())
            .first()
        )
        return row[0] if row else None
