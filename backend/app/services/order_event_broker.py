"""OrderEventBroker (contract frozen in Phase 0; in-memory pub/sub implemented by U5/D).

Real-time SSE propagation. Events published AFTER commit. Signatures per component-methods.md §1.6.
"""
from collections.abc import AsyncIterator
from typing import Protocol

from app.schemas.common import OrderView


class OrderEvent(dict):
    """{'type': 'order_created'|'order_updated'|'order_deleted', 'payload': OrderView | {order_id}}"""


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


class _NotImplementedBroker:
    """Phase 0 placeholder. U5/D provides the real in-memory implementation."""

    def subscribe(self, store_id: int) -> AsyncIterator[OrderEvent]:
        raise NotImplementedError("OrderEventBroker.subscribe — implemented in U5/D")

    def unsubscribe(self, subscriber_id: str) -> None:
        raise NotImplementedError("OrderEventBroker.unsubscribe — implemented in U5/D")

    def publish(self, event: OrderEvent) -> None:
        raise NotImplementedError("OrderEventBroker.publish — implemented in U5/D")

    def snapshot(self, store_id: int, table_filter: int | None = None) -> list[OrderView]:
        raise NotImplementedError("OrderEventBroker.snapshot — implemented in U5/D")


# Shared singleton reference; U5/D swaps in the real broker instance.
broker: OrderEventBroker = _NotImplementedBroker()
