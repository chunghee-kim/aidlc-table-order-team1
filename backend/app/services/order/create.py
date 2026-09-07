"""U4/C — order creation, current-session listing, admin snapshot.

Owned by stream C. Consumes frozen contracts only:
  - TableSessionService.get_or_start_active_session (U6/E) — session ensure delegation (§2.1)
  - Menu model as the unit-price source of truth (MenuRepo contract, impl by U3/B)
  - OrderEventBroker.publish (U5/D) — post-commit realtime event source (§2.2)

🔬 PBT invariants (US-C-08/12): total = Σ(unit_price × quantity); quantity >= 1;
order total == cart total. Pure helpers below (`line_total`, `order_total`) are the tested core.
"""
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.errors import AppError, ErrorCode
from app.models import Menu, Order, OrderItem
from app.repositories.order import SqlOrderRepo
from app.schemas.common import OrderItemView, OrderView, PageParams
from app.schemas.order import OrderItemInput, OrderPage
from app.services import table_session
from app.services.order_event_broker import OrderEvent, broker

# NFR-4 (사용성): 항목당 수량 상한. 항목(메뉴) 종류 수는 무제한.
MAX_QUANTITY = 99
# NFR-1 (성능/동시성): order_number UNIQUE 위반 시 재채번 재시도 횟수.
MAX_NUMBER_RETRIES = 5


# --- Pure, side-effect-free core (🔬 PBT target) -------------------------------------------

class PricedItem:
    """A cart line resolved against the menu source of truth."""

    __slots__ = ("menu_id", "menu_name", "unit_price", "quantity")

    def __init__(self, menu_id: int, menu_name: str, unit_price: int, quantity: int):
        self.menu_id = menu_id
        self.menu_name = menu_name
        self.unit_price = unit_price
        self.quantity = quantity


def line_total(unit_price: int, quantity: int) -> int:
    return unit_price * quantity


def order_total(priced: list[PricedItem]) -> int:
    """Order total = Σ(unit_price × quantity) — must equal the cart total (US-C-12)."""
    return sum(line_total(p.unit_price, p.quantity) for p in priced)


def next_order_number(prefix: str, last_number: str | None) -> str:
    """`YYYYMMDD-###`, daily sequence (business-rules.md §2). `last_number` is today's max."""
    if last_number is None:
        seq = 1
    else:
        seq = int(last_number.split("-", 1)[1]) + 1
    return f"{prefix}-{seq:03d}"


def _validate_items(items: list[OrderItemInput]) -> None:
    if not items:
        raise AppError(ErrorCode.VALIDATION_ERROR, "장바구니가 비어 있습니다.")
    for it in items:
        if it.quantity < 1 or it.quantity > MAX_QUANTITY:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"수량은 1~{MAX_QUANTITY} 범위여야 합니다.",
                {"menu_id": it.menu_id, "quantity": it.quantity},
            )


def _to_view(order: Order) -> OrderView:
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

def create_order(session_ctx: Any, items: list[OrderItemInput]) -> OrderView:
    """Create an order: ensure session, snapshot prices, total, number, publish order_created."""
    _validate_items(items)

    db = SessionLocal()
    try:
        repo = SqlOrderRepo(db)

        # Session ensure — delegated to U6/E contract (§2.1). <=1 active session per table.
        session_id = getattr(session_ctx, "session_id", None)
        if session_id is None:
            session = table_session.get_or_start_active_session(session_ctx.table_id)
            session_id = getattr(session, "id", session)

        # Resolve prices from the menu source of truth (integration: MenuRepo.list_by_store).
        menu_ids = [it.menu_id for it in items]
        menus = {
            m.id: m
            for m in db.query(Menu)
            .filter(Menu.store_id == session_ctx.store_id, Menu.id.in_(menu_ids))
            .all()
        }
        missing = [mid for mid in menu_ids if mid not in menus]
        if missing:
            raise AppError(ErrorCode.NOT_FOUND, "존재하지 않는 메뉴가 포함되어 있습니다.", {"menu_ids": missing})

        priced = [
            PricedItem(m.id, m.name, m.price, it.quantity)
            for it in items
            for m in [menus[it.menu_id]]
        ]
        total = order_total(priced)

        prefix = datetime.utcnow().strftime("%Y%m%d")

        # NFR-1: 채번은 order_number UNIQUE 제약 + 재시도로 동시성 안전(§ nfr-design.md).
        # 커밋 시 UNIQUE 충돌이 나면 롤백 후 오늘자 최대번호를 다시 읽어 재채번한다.
        order = None
        for attempt in range(MAX_NUMBER_RETRIES):
            order_number = next_order_number(
                prefix, repo.max_order_number_today(session_ctx.store_id, prefix)
            )
            order = Order(
                session_id=session_id,
                table_id=session_ctx.table_id,
                order_number=order_number,
                status="대기중",
                total_amount=total,
            )
            order_items = [
                OrderItem(menu_id=p.menu_id, menu_name=p.menu_name, unit_price=p.unit_price, quantity=p.quantity)
                for p in priced
            ]
            repo.create(order, order_items)
            try:
                db.commit()
                break
            except IntegrityError:
                db.rollback()
                if attempt == MAX_NUMBER_RETRIES - 1:
                    raise AppError(
                        ErrorCode.CONFLICT,
                        "주문번호 생성이 반복해서 충돌했습니다. 잠시 후 다시 시도해주세요.",
                    )
                # 다음 루프에서 max_order_number_today를 다시 조회해 재채번한다.

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

    # Publish AFTER commit (§2.2). Best-effort: realtime failure must not fail the order.
    try:
        broker.publish(OrderEvent(type="order_created", payload=view))
    except Exception:  # noqa: BLE001 — broker not yet wired (U5/D) or transient; ignore.
        pass

    return view


def list_current_session_orders(session_id: int, page: Any) -> OrderPage:
    """List the current session's orders in time order, cursor-paginated (US-C-14)."""
    params = page if isinstance(page, PageParams) else PageParams(**(page or {}))
    db = SessionLocal()
    try:
        repo = SqlOrderRepo(db)
        rows = repo.list_by_session_page(session_id, params.cursor, params.limit + 1)
        has_more = len(rows) > params.limit
        rows = rows[: params.limit]
        next_cursor = rows[-1].id if has_more and rows else None
        return OrderPage(items=[_to_view(o) for o in rows], next_cursor=next_cursor)
    finally:
        db.close()


def list_admin_orders(store_id: int, table_filter: int | None = None) -> list[OrderView]:
    """Admin dashboard initial snapshot of active orders (US-A-05/08)."""
    db = SessionLocal()
    try:
        repo = SqlOrderRepo(db)
        return [_to_view(o) for o in repo.list_active_by_store(store_id, table_filter)]
    finally:
        db.close()
