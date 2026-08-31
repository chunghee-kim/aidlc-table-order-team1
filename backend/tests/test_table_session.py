"""U2/A — table setup (US-A-04) and tablet auto-login identity (US-C-01/02)."""
from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    STORE_CODE,
    TABLE_NUMBER,
    TABLE_PASSWORD,
)


def _admin_headers(client) -> dict[str, str]:
    res = client.post("/api/admin/login", json={
        "store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    })
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_setup_requires_admin_auth(client):
    res = client.post("/api/admin/tables/1/setup", json={"table_number": 7, "table_password": "7"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_setup_creates_new_table_and_enables_auto_login(client):
    headers = _admin_headers(client)
    res = client.post("/api/admin/tables/1/setup",
                      json={"table_number": 9, "table_password": "pass9"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["table_number"] == 9
    assert body["auto_login_enabled"] is True
    assert body["table_id"] >= 1

    # The newly provisioned table can now auto-login.
    login = client.post("/api/customer/table-login",
                        json={"store_code": STORE_CODE, "table_number": 9, "table_password": "pass9"})
    assert login.status_code == 200
    assert login.json()["table_id"] == body["table_id"]


def test_setup_overwrites_existing_table_password(client):
    headers = _admin_headers(client)
    # Re-provision the seeded TABLE_NUMBER with a new password.
    res = client.post(f"/api/admin/tables/1/setup",
                      json={"table_number": TABLE_NUMBER, "table_password": "newpass"}, headers=headers)
    assert res.status_code == 200

    # Old password no longer works; new one does.
    old = client.post("/api/customer/table-login",
                      json={"store_code": STORE_CODE, "table_number": TABLE_NUMBER, "table_password": TABLE_PASSWORD})
    assert old.status_code == 401
    new = client.post("/api/customer/table-login",
                      json={"store_code": STORE_CODE, "table_number": TABLE_NUMBER, "table_password": "newpass"})
    assert new.status_code == 200


def test_setup_rejects_invalid_input(client):
    headers = _admin_headers(client)
    assert client.post("/api/admin/tables/1/setup",
                       json={"table_number": 0, "table_password": "x"}, headers=headers).status_code == 422
    assert client.post("/api/admin/tables/1/setup",
                       json={"table_number": 3, "table_password": "  "}, headers=headers).status_code == 422


def test_table_login_unknown_store_is_not_found(client):
    res = client.post("/api/customer/table-login",
                      json={"store_code": "NOPE", "table_number": 1, "table_password": "1"})
    assert res.status_code == 404


def test_table_login_unknown_table_is_not_found(client):
    res = client.post("/api/customer/table-login",
                      json={"store_code": STORE_CODE, "table_number": 999, "table_password": "x"})
    assert res.status_code == 404


def test_table_login_wrong_password_is_unauthorized(client):
    res = client.post("/api/customer/table-login",
                      json={"store_code": STORE_CODE, "table_number": TABLE_NUMBER, "table_password": "nope"})
    assert res.status_code == 401
