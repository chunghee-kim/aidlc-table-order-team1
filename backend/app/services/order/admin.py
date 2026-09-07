"""U5/D — admin order monitoring writes: status transition + authoritative delete.

Owned by stream D. Consumes frozen contracts only:
  - OrderRepo (U4/C) — get / update_status / delete / sum_total_by_table
  - OrderEventBroker.publish (U5/D) — post-commit realtime fan-out (BR-U5-10)
  - AdminContext (U2/A) — actor identity (store_id) for store-scoped events

🔬 PBT invariants (US-A-09/10):
  - BR-U5-1/2: transitions match ALLOWED exactly; forward-only, 완료 is terminal.
  - BR-U5-5: after delete, table total == sum of the remaining active orders.
The pure helpers below (`is_allowed_transition`, `remaining_total`) are the tested core.
"""
from typing import Any

from app.db import SessionLocal
from app.errors import AppError, ErrorCode
from app.repositories.order import SqlOrderRepo
from app.schemas.admin_order import AdminOrderView, TableTotals
from app.schemas.common import OrderItemView, OrderView
from app.services.order_event_broker import OrderEvent, broker

# --- Pure, side-effect-free core (🔬 PBT target) -------------------------------------------

VALID_STATUSES = ("대기중", "준비중", "완료")

# Forward-only, adjacent transitions (BR-U5-1). 완료 is terminal (BR-U5-2).
ALLOWED: dict[str, set[str]] = {"대기중": {"준비중"}, "준비중": {"완료"}, "완료": set()}


def is_allowed_transition(current: str, nxt: str) -> bool:
    """True iff `current -> nxt` is a permitted transition (excludes no-op X->X)."""
    return nxt in ALLOWED.get(current, set())


def remaining_total(totals: list[int], deleted_index: int) -> int:
    """Table total after removing one order (BR-U5-5). Pure arithmetic over per-order totals."""
    return sum(t for i, t in enumerate(totals) if i != deleted_index)


def _validate_transition(current: str, nxt: str) -> None:
    """Raise VALIDATION_ERROR(422) for an unknown status, CONFLICT(409) for a disallowed move."""
    if nxt not in VALID_STATUSES:
        raise AppError(ErrorCode.VALIDATION_ERROR, "알 수 없는 주문 상태입니다.", {"status": nxt})
    if not is_allowed_transition(current, nxt):
        raise AppError(
            ErrorCode.CONFLICT,
            f"'{current}'에서 '{nxt}'(으)로 변경할 수 없습니다.",
            {"current": current, "requested": nxt},
        )


def _to_view(order: Any) -> OrderView:
    return OrderView(
        order_number=order.order_number,
        table_id=order.table_id,
        session_id=order.session_id,
        items=[
            OrderItemView(menu_name=i.menu_name, unit_price=i.unit_price, quantity=i.quantity)
            for i in order.items
        ],
        total_amount=order.total_amount,
        status=order.status,
        created_at=order.created_at,
    )


# --- Service methods (wired into the facade in __init__.py) --------------------------------

def list_admin_orders_detailed(store_id: int, table_filter: int | None = None) -> list[AdminOrderView]:
    """Admin dashboard initial snapshot with order_id (US-A-05/08). Active sessions only (BR-U5-7)."""
    db = SessionLocal()
    try:
        rows = SqlOrderRepo(db).list_active_by_store(store_id, table_filter)
        return [
            AdminOrderView(
                order_id=o.id,
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


def change_status(order_id: int, next_status: str, actor: Any) -> OrderView:
    """Transition an order's status (대기중→준비중→완료). Allowed moves only; publish order_updated."""
    db = SessionLocal()
    try:
        repo = SqlOrderRepo(db)
        order = repo.get(order_id)
        if order is None:
            raise AppError(ErrorCode.NOT_FOUND, "주문을 찾을 수 없습니다.", {"order_id": order_id})

        _validate_transition(order.status, next_status)  # 422/409 before any mutation (BR-U5-1).

        repo.update_status(order_id, next_status)
        db.commit()
        db.refresh(order)
        view = _to_view(order)
    except AppError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # Publish AFTER commit (BR-U5-10). Best-effort: realtime failure must not fail the write.
    try:
        broker.publish(
            OrderEvent(type="order_updated", payload=view, order_id=order_id, store_id=actor.store_id)
        )
    except Exception:  # noqa: BLE001
        pass

    return view


def delete_order(order_id: int, actor: Any) -> TableTotals:
    """Authoritative delete of an active-session order (status-agnostic). Recompute + publish."""
    db = SessionLocal()
    try:
        repo = SqlOrderRepo(db)
        order = repo.get(order_id)
        if order is None:
            raise AppError(ErrorCode.NOT_FOUND, "주문을 찾을 수 없습니다.", {"order_id": order_id})

        table_id = order.table_id
        repo.delete(order_id)  # OrderItem cascades (model: delete-orphan).
        new_total = repo.sum_total_by_table(table_id)  # remaining active-session sum (BR-U5-5).
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    try:
        broker.publish(
            OrderEvent(
                type="order_deleted",
                order_id=order_id,
                table_id=table_id,
                table_total=new_total,
                store_id=actor.store_id,
            )
        )
    except Exception:  # noqa: BLE001
        pass

    return TableTotals(table_id=table_id, total_amount=new_total)
