"""MenuRouter integration tests (U3/B) via TestClient with overridden DB + admin deps."""
import pytest
from fastapi.testclient import TestClient

from app.auth.dependency import AdminContext, get_current_admin
from app.db import get_db
from app.main import app


@pytest.fixture()
def client(db_session, store):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_admin] = lambda: AdminContext(admin_id=1, store_id=store.id)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_public_endpoints_open_and_admin_crud_roundtrip(client, category):
    # public listing works without auth
    assert client.get("/api/categories").json() == [
        {"id": category.id, "name": "커피", "display_order": 0}
    ]
    assert client.get("/api/menus").json() == []

    # admin create
    res = client.post(
        "/api/admin/menus",
        json={"name": "아메리카노", "price": 4000, "category_id": category.id, "description": "쓴 커피"},
    )
    assert res.status_code == 201
    menu = res.json()
    assert menu["price"] == 4000 and menu["is_available"] is True

    # now visible to customers
    listed = client.get("/api/menus").json()
    assert [m["name"] for m in listed] == ["아메리카노"]

    # update
    res = client.put(
        f"/api/admin/menus/{menu['id']}",
        json={"name": "카페라떼", "price": 4500, "category_id": category.id},
    )
    assert res.status_code == 200 and res.json()["name"] == "카페라떼"

    # delete
    assert client.delete(f"/api/admin/menus/{menu['id']}").status_code == 204
    assert client.get("/api/menus").json() == []


def test_create_invalid_price_returns_422(client, category):
    res = client.post(
        "/api/admin/menus",
        json={"name": "잘못된메뉴", "price": 0, "category_id": category.id},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reorder_endpoint(client, category):
    ids = [
        client.post("/api/admin/menus", json={"name": n, "price": 1000, "category_id": category.id}).json()["id"]
        for n in ("A", "B", "C")
    ]
    res = client.patch(
        f"/api/admin/categories/{category.id}/menu-order",
        json={"ordered_menu_ids": [ids[2], ids[0], ids[1]]},
    )
    assert res.status_code == 204
    assert [m["name"] for m in client.get("/api/menus").json()] == ["C", "A", "B"]
