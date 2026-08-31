"""MenuService tests (U3/B) — PBT 🔬 (price > 0, required fields) + CRUD/ordering units."""
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.auth.dependency import AdminContext
from app.errors import AppError, ErrorCode
from app.models import Category
from app.schemas.menu import MenuInput
from app.services.menu_service import MenuService

# db_session/store/category are function-scoped; suppress Hypothesis's re-use health check.
_SUPPRESS = [HealthCheck.function_scoped_fixture]


def _actor(store) -> AdminContext:
    return AdminContext(admin_id=1, store_id=store.id)


# ---- PBT 🔬: price invariant (US-A-16) ----
@settings(suppress_health_check=_SUPPRESS, max_examples=50)
@given(price=st.integers(max_value=0))
def test_create_rejects_nonpositive_price(db_session, store, category, price):
    svc = MenuService(db_session)
    data = MenuInput(name="아메리카노", price=price, category_id=category.id)
    with pytest.raises(AppError) as exc:
        svc.create_menu(data, _actor(store))
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert "price" in exc.value.details["fields"]


# ---- PBT 🔬: required-field invariant (US-A-16) ----
@settings(suppress_health_check=_SUPPRESS, max_examples=25)
@given(name=st.sampled_from(["", " ", "   ", "\t", "\n", "  \t \n"]))
def test_create_rejects_blank_name(db_session, store, category, name):
    svc = MenuService(db_session)
    data = MenuInput(name=name, price=4000, category_id=category.id)
    with pytest.raises(AppError) as exc:
        svc.create_menu(data, _actor(store))
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert "name" in exc.value.details["fields"]


# ---- PBT 🔬: valid input always persists and round-trips ----
@settings(suppress_health_check=_SUPPRESS, max_examples=50)
@given(
    price=st.integers(min_value=1, max_value=10_000_000),
    name=st.text(min_size=1, max_size=100).filter(lambda s: bool(s.strip())),
)
def test_create_persists_valid_menu(db_session, store, category, price, name):
    svc = MenuService(db_session)
    view = svc.create_menu(
        MenuInput(name=name, price=price, category_id=category.id, description="설명"),
        _actor(store),
    )
    assert view.price == price
    assert view.category_id == category.id
    assert view.is_available is True
    assert view.id is not None


# ---- unit: create rejects a category from another store ----
def test_create_rejects_foreign_category(db_session, store, category):
    other = Category(store_id=store.id + 999, name="타매장", display_order=0)
    db_session.add(other)
    db_session.commit()
    svc = MenuService(db_session)
    with pytest.raises(AppError) as exc:
        svc.create_menu(MenuInput(name="라떼", price=4500, category_id=other.id), _actor(store))
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


# ---- unit: update / delete / not-found ----
def test_update_menu_changes_fields(db_session, store, category):
    svc = MenuService(db_session)
    created = svc.create_menu(MenuInput(name="라떼", price=4500, category_id=category.id), _actor(store))
    updated = svc.update_menu(
        created.id,
        MenuInput(name="바닐라라떼", price=5000, category_id=category.id, description="달콤"),
        _actor(store),
    )
    assert updated.name == "바닐라라떼"
    assert updated.price == 5000
    assert updated.description == "달콤"


def test_update_missing_menu_raises_not_found(db_session, store, category):
    svc = MenuService(db_session)
    with pytest.raises(AppError) as exc:
        svc.update_menu(9999, MenuInput(name="x", price=1000, category_id=category.id), _actor(store))
    assert exc.value.code == ErrorCode.NOT_FOUND


def test_delete_menu_removes_it(db_session, store, category):
    svc = MenuService(db_session)
    created = svc.create_menu(MenuInput(name="에이드", price=5000, category_id=category.id), _actor(store))
    svc.delete_menu(created.id, _actor(store))
    assert all(m.id != created.id for m in svc.list_menus_for_customer(store.id))


def test_delete_missing_menu_raises_not_found(db_session, store, category):
    svc = MenuService(db_session)
    with pytest.raises(AppError) as exc:
        svc.delete_menu(9999, _actor(store))
    assert exc.value.code == ErrorCode.NOT_FOUND


# ---- unit: reorder + customer ordering ----
def test_reorder_menus_updates_display_order(db_session, store, category):
    svc = MenuService(db_session)
    a = svc.create_menu(MenuInput(name="A", price=1000, category_id=category.id), _actor(store))
    b = svc.create_menu(MenuInput(name="B", price=1000, category_id=category.id), _actor(store))
    c = svc.create_menu(MenuInput(name="C", price=1000, category_id=category.id), _actor(store))

    svc.reorder_menus(category.id, [c.id, a.id, b.id], _actor(store))

    ordered = [m.name for m in svc.list_menus_for_customer(store.id)]
    assert ordered == ["C", "A", "B"]


def test_customer_listing_sorted_by_category_then_order(db_session, store):
    coffee = Category(store_id=store.id, name="커피", display_order=0)
    dessert = Category(store_id=store.id, name="디저트", display_order=1)
    db_session.add_all([coffee, dessert])
    db_session.commit()
    svc = MenuService(db_session)
    svc.create_menu(MenuInput(name="케이크", price=6000, category_id=dessert.id), _actor(store))
    svc.create_menu(MenuInput(name="아메리카노", price=4000, category_id=coffee.id), _actor(store))

    names = [m.name for m in svc.list_menus_for_customer(store.id)]
    assert names == ["아메리카노", "케이크"]  # coffee (order 0) before dessert (order 1)


def test_empty_store_returns_empty_lists(db_session):
    svc = MenuService(db_session)
    assert svc.default_store_id() is None
    assert svc.list_menus_for_customer(None) == []
    assert svc.list_categories(None) == []
