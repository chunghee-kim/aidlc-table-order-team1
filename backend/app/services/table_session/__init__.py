"""TableSessionService facade (contract frozen in Phase 0).

Split by owner (1 file = 1 stream):
  - identify.py  (U2/A): setup_table, resolve_session_context
  - lifecycle.py (U6/E): get_or_start_active_session, close_table
Phase 0 freezes the protocol + facade stubs. Each stream adds its submodule and wires the
facade below (1~2 lines). Do NOT change these signatures without owner+consumer agreement.
Signatures per component-methods.md §1.2.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TableSessionContext:
    store_id: int
    table_id: int
    session_id: int | None = None


@dataclass
class TableSetupResult:
    table_id: int
    table_number: int
    auto_login_enabled: bool


@dataclass
class CloseResult:
    moved_order_count: int
    closed_at: datetime


# --- U2/A (identify.py) ---
def setup_table(store_id: int, table_number: int, table_password: str, actor: Any) -> TableSetupResult:
    """Tablet initial setup: store number/password, enable auto-login (US-A-04)."""
    raise NotImplementedError("setup_table — implemented in U2/A (services/table_session/identify.py)")


def resolve_session_context(store_code: str, table_number: int, table_password: str) -> TableSessionContext:
    """Tablet auto-login: restore store/table identity context (US-C-01/02)."""
    raise NotImplementedError("resolve_session_context — implemented in U2/A (identify.py)")


# --- U6/E (lifecycle.py) ---
def get_or_start_active_session(table_id: int) -> Any:
    """Return active session or start a new one. Invariant: <=1 active per table (US-A-11)."""
    raise NotImplementedError("get_or_start_active_session — implemented in U6/E (lifecycle.py)")


def close_table(table_id: int, actor: Any) -> CloseResult:
    """Close usage: migrate orders -> OrderHistory losslessly + reset (US-A-12)."""
    raise NotImplementedError("close_table — implemented in U6/E (lifecycle.py)")
