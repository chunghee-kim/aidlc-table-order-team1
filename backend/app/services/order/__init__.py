"""OrderService facade (contract frozen in Phase 0).

Split by owner (1 file = 1 stream):
  - create.py (U4/C): create_order, list_current_session_orders, list_admin_orders
  - admin.py  (U5/D): change_status, delete_order
Phase 0 freezes the facade stubs. Each stream adds its submodule and wires the facade below.
Signatures per component-methods.md §1.4. Do NOT change without owner+consumer agreement.
"""
from typing import Any

from app.schemas.admin_order import TableTotals
from app.schemas.common import OrderView
from app.schemas.order import OrderItemInput, OrderPage

# --- U4/C (create.py) --- wired by stream C
from app.services.order import create as _create


def create_order(session_ctx: Any, items: list[OrderItemInput]) -> OrderView:
    """Create order: ensure session, total=Σ(unit_price×qty), assign number, publish order_created."""
    return _create.create_order(session_ctx, items)


def list_current_session_orders(session_id: int, page: Any) -> OrderPage:
    """List current session's orders in time order (US-C-14)."""
    return _create.list_current_session_orders(session_id, page)


def list_admin_orders(store_id: int, table_filter: int | None = None) -> list[OrderView]:
    """Admin dashboard initial snapshot (US-A-05/08)."""
    return _create.list_admin_orders(store_id, table_filter)


# --- U5/D (admin.py) ---
def change_status(order_id: int, next_status: str, actor: Any) -> OrderView:
    """Status transition (대기중→준비중→완료); allowed transitions only. Publish order_updated."""
    raise NotImplementedError("change_status — implemented in U5/D (services/order/admin.py)")


def delete_order(order_id: int, actor: Any) -> TableTotals:
    """Admin delete + recompute table total (= remaining sum). Publish order_deleted."""
    raise NotImplementedError("delete_order — implemented in U5/D (admin.py)")
