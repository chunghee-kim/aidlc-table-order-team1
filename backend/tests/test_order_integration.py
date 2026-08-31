"""U4/C integration — create_order + list_current_session_orders against an isolated DB.

Uses a fresh in-memory SQLite engine and stubs the U6/E session-ensure contract
(`get_or_start_active_session`) and the U5/D broker, per "contract delegation only".
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.errors import AppError, ErrorCode
from app.models import Category, Menu, Order, Store, Table, TableSession
from app.schemas.common import PageParams
from app.schemas.order import OrderItemInput
from app.services import order as order_service
from app.services.order import create as create_mod
from app.services.table_session import TableSessionContext


@pytest.fixture()
def db_factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Seed a store / table / active session / category / two menus.
    s = TestSession()
    store = Store(store_code="T01", name="테스트")
    s.add(store)
    s.flush()
    table = Table(store_id=store.id, table_number=1, table_password_hash="x")
    s.add(table)
    s.flush()
    session = TableSession(table_id=table.id, status="active")
    s.add(session)
    cat = Category(store_id=store.id, name="커피", display_order=0)
    s.add(cat)
    s.flush()
    m1 = Menu(store_id=store.id, category_id=cat.id, name="아메리카노", price=4000, display_order=0)
    m2 = Menu(store_id=store.id, category_id=cat.id, name="라떼", price=4500, display_order=1)
    s.add_all([m1, m2])
    s.commit()
    ids = {"store": store.id, "table": table.id, "session": session.id, "m1": m1.id, "m2": m2.id}
    s.close()

    # Route the service's SessionLocal at our engine; stub the U6 contract + U5 broker.
    monkeypatch.setattr(create_mod, "SessionLocal", TestSession)
    monkeypatch.setattr(
        create_mod.table_session,
        "get_or_start_active_session",
        lambda table_id: type("S", (), {"id": ids["session"]})(),
    )
    monkeypatch.setattr(create_mod.broker, "publish", lambda event: None)
    return TestSession, ids


def test_create_order_computes_total_and_number(db_factory):
    _, ids = db_factory
    ctx = TableSessionContext(store_id=ids["store"], table_id=ids["table"], session_id=ids["session"])
    view = order_service.create_order(
        ctx, [OrderItemInput(menu_id=ids["m1"], quantity=2), OrderItemInput(menu_id=ids["m2"], quantity=1)]
    )
    assert view.total_amount == 4000 * 2 + 4500  # 12500
    assert view.order_number.endswith("-001")
    assert view.status == "대기중"
    assert view.session_id == ids["session"]
    assert {i.menu_name for i in view.items} == {"아메리카노", "라떼"}


def test_order_number_increments_per_day(db_factory):
    _, ids = db_factory
    ctx = TableSessionContext(store_id=ids["store"], table_id=ids["table"], session_id=ids["session"])
    v1 = order_service.create_order(ctx, [OrderItemInput(menu_id=ids["m1"], quantity=1)])
    v2 = order_service.create_order(ctx, [OrderItemInput(menu_id=ids["m1"], quantity=1)])
    assert v1.order_number.endswith("-001")
    assert v2.order_number.endswith("-002")


def test_unknown_menu_rejected(db_factory):
    _, ids = db_factory
    ctx = TableSessionContext(store_id=ids["store"], table_id=ids["table"], session_id=ids["session"])
    with pytest.raises(AppError) as exc:
        order_service.create_order(ctx, [OrderItemInput(menu_id=999999, quantity=1)])
    assert exc.value.code == ErrorCode.NOT_FOUND


def test_list_current_session_orders_pagination(db_factory):
    TestSession, ids = db_factory
    ctx = TableSessionContext(store_id=ids["store"], table_id=ids["table"], session_id=ids["session"])
    for _ in range(3):
        order_service.create_order(ctx, [OrderItemInput(menu_id=ids["m1"], quantity=1)])

    page1 = order_service.list_current_session_orders(ids["session"], PageParams(cursor=None, limit=2))
    assert len(page1.items) == 2
    assert page1.next_cursor is not None

    page2 = order_service.list_current_session_orders(ids["session"], PageParams(cursor=page1.next_cursor, limit=2))
    assert len(page2.items) == 1
    assert page2.next_cursor is None


def test_current_session_excludes_other_sessions(db_factory):
    TestSession, ids = db_factory
    ctx = TableSessionContext(store_id=ids["store"], table_id=ids["table"], session_id=ids["session"])
    order_service.create_order(ctx, [OrderItemInput(menu_id=ids["m1"], quantity=1)])

    # A different (closed) session must not appear in the current-session listing.
    s = TestSession()
    other = TableSession(table_id=ids["table"], status="closed")
    s.add(other)
    s.commit()
    other_id = other.id
    s.close()

    page = order_service.list_current_session_orders(other_id, PageParams(cursor=None, limit=20))
    assert page.items == []
