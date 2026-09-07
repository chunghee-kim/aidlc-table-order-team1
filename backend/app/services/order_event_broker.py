"""OrderEventBroker (contract frozen in Phase 0; in-memory pub/sub implemented by U5/D).

Real-time SSE propagation. Events are published AFTER commit (BR-U5-10). Fan-out is scoped to a
store's subscribers (BR-U5-12). Signatures per component-methods.md §1.6.

Cross-thread note: FastAPI runs sync path operations (create/change_status/delete) in a worker
thread, while the SSE endpoint's async generator runs on the event loop. Each subscriber captures
its running loop at subscribe() time; publish() hands events to that loop via
`loop.call_soon_threadsafe`, which is the safe way to feed an asyncio.Queue from another thread.
"""
import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any, Protocol

from app.schemas.common import OrderItemView, OrderView

# Bounded per-subscriber queue. A consumer that falls this far behind is dropped; it recovers the
# full state via the snapshot frame on reconnect (BR-U5-12/14).
_QUEUE_MAXSIZE = 1000


class OrderEvent(dict):
    """{'type': 'order_created'|'order_updated'|'order_deleted', 'payload': OrderView | {order_id}}.

    U5/D also attaches routing/serialization hints (`order_id`, `store_id`, `table_id`,
    `table_total`) as extra keys; the broker builds the SSE frame from them.
    """


class OrderEventBroker(Protocol):
    def subscribe(self, store_id: int) -> AsyncIterator[OrderEvent]:
        """Register an SSE subscriber -> asyncio queue-backed event stream."""
        ...

    def unsubscribe(self, subscriber_id: str) -> None:
        ...

    def publish(self, event: OrderEvent) -> None:
        """Broadcast order_created/updated/deleted to the store's subscribers."""
        ...

    def snapshot(self, store_id: int, table_filter: int | None = None) -> list[OrderView]:
        """Full snapshot of currently active orders (reconnect recovery, US-A-06)."""
        ...


# --- Serialization helpers -----------------------------------------------------------------
# The frozen `OrderView` schema carries no `order_id`; the design (business-logic-model §6) says
# the router/broker serialization layer attaches it. These build the SSE "admin order" dict.

def _order_row_to_admin(order: Any) -> dict:
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "session_id": order.session_id,
        "items": [
            {"menu_name": i.menu_name, "unit_price": i.unit_price, "quantity": i.quantity}
            for i in order.items
        ],
        "total_amount": order.total_amount,
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _view_to_admin(view: OrderView, order_id: int) -> dict:
    d = view.model_dump(mode="json")
    d["order_id"] = order_id
    return d


class _Subscriber:
    __slots__ = ("id", "store_id", "queue", "loop")

    def __init__(self, store_id: int, loop: asyncio.AbstractEventLoop):
        self.id = str(uuid.uuid4())
        self.store_id = store_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self.loop = loop


class InMemoryOrderBroker:
    """In-memory pub/sub for a single process (MVP). Store-scoped fan-out; snapshot on subscribe."""

    def __init__(self) -> None:
        self._subs: dict[str, _Subscriber] = {}

    async def subscribe(self, store_id: int, table_filter: int | None = None) -> AsyncIterator[dict]:
        loop = asyncio.get_running_loop()
        sub = _Subscriber(store_id, loop)
        self._subs[sub.id] = sub
        try:
            # BR-U5-14: emit a full snapshot first so a (re)connecting client converges immediately.
            yield {"type": "snapshot", "orders": self._active_order_frames(store_id, table_filter)}
            while True:
                yield await sub.queue.get()
        finally:
            self._subs.pop(sub.id, None)

    def unsubscribe(self, subscriber_id: str) -> None:
        self._subs.pop(subscriber_id, None)

    def publish(self, event: OrderEvent) -> None:
        if not self._subs:  # nobody listening — skip all work (incl. the created lookup).
            return
        frame, store_id = self._build_frame(event)
        if frame is None or store_id is None:
            return
        for sub in list(self._subs.values()):
            if sub.store_id != store_id:
                continue
            try:
                sub.loop.call_soon_threadsafe(self._deliver, sub, frame)
            except RuntimeError:
                # Loop already closed (client gone) — drop the subscriber.
                self._subs.pop(sub.id, None)

    @staticmethod
    def _deliver(sub: _Subscriber, frame: dict) -> None:
        try:
            sub.queue.put_nowait(frame)
        except asyncio.QueueFull:
            # Slow consumer (BR-U5-12): drop it; the client reconnects and re-snapshots.
            pass

    def snapshot(self, store_id: int, table_filter: int | None = None) -> list[OrderView]:
        """Protocol-typed snapshot (list[OrderView]); the stream uses `_active_order_frames`."""
        from app.db import SessionLocal
        from app.repositories.order import SqlOrderRepo

        db = SessionLocal()
        try:
            rows = SqlOrderRepo(db).list_active_by_store(store_id, table_filter)
            return [
                OrderView(
                    order_number=o.order_number,
                    table_id=o.table_id,
                    session_id=o.session_id,
                    items=[
                        OrderItemView(menu_name=i.menu_name, unit_price=i.unit_price, quantity=i.quantity)
                        for i in o.items
                    ],
                    total_amount=o.total_amount,
                    status=o.status,
                    created_at=o.created_at,
                )
                for o in rows
            ]
        finally:
            db.close()

    # --- internals -------------------------------------------------------------------------

    def _active_order_frames(self, store_id: int, table_filter: int | None = None) -> list[dict]:
        from app.db import SessionLocal
        from app.repositories.order import SqlOrderRepo

        db = SessionLocal()
        try:
            return [_order_row_to_admin(o) for o in SqlOrderRepo(db).list_active_by_store(store_id, table_filter)]
        finally:
            db.close()

    def _build_frame(self, event: OrderEvent) -> tuple[dict | None, int | None]:
        etype = event.get("type")
        if etype == "order_deleted":
            return (
                {
                    "type": "order_deleted",
                    "order_id": event.get("order_id"),
                    "table_id": event.get("table_id"),
                    "table_total": event.get("table_total"),
                },
                event.get("store_id"),
            )

        if etype == "order_updated":
            view = event.get("payload")
            order_id = event.get("order_id")
            store_id = event.get("store_id")
            if view is None or order_id is None:
                return (None, None)
            return ({"type": "order_updated", "order": _view_to_admin(view, order_id)}, store_id)

        if etype == "order_created":
            # Published by U4/create.py with payload=OrderView (no id/store). Resolve both from the
            # unique order_number (order is already committed by the time this runs).
            view = event.get("payload")
            if view is None:
                return (None, None)
            from app.db import SessionLocal
            from app.models import Order, Table

            db = SessionLocal()
            try:
                row = (
                    db.query(Order)
                    .join(Table, Order.table_id == Table.id)
                    .filter(Order.order_number == view.order_number)
                    .first()
                )
                if row is None:
                    return (None, None)
                store_id = db.query(Table.store_id).filter(Table.id == row.table_id).scalar()
                return ({"type": "order_created", "order": _order_row_to_admin(row)}, store_id)
            finally:
                db.close()

        return (None, None)


# Shared singleton reference. Consumers import this name; U5/D provides the real implementation.
broker: OrderEventBroker = InMemoryOrderBroker()
