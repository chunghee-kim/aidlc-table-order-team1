"""U2/A — admin authentication (US-A-01/02/03)."""
from datetime import datetime, timedelta, timezone

import jwt

from app.services import auth_service
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, STORE_CODE


def test_login_success_returns_token_and_admin(client):
    res = client.post("/api/admin/login", json={
        "store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["token"]
    assert body["admin"]["username"] == ADMIN_USERNAME
    assert body["admin"]["store_id"] >= 1

    # Issued token verifies to the same admin/store context.
    ctx = auth_service.verify_token(body["token"])
    assert ctx.admin_id == body["admin"]["id"]
    assert ctx.store_id == body["admin"]["store_id"]


def test_login_wrong_password_is_unauthorized(client):
    res = client.post("/api/admin/login", json={
        "store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": "wrong",
    })
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_unknown_store_is_unauthorized(client):
    res = client.post("/api/admin/login", json={
        "store_code": "NOPE", "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    })
    assert res.status_code == 401


def test_login_lockout_after_five_failures(client):
    payload = {"store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": "bad"}
    for _ in range(5):
        assert client.post("/api/admin/login", json=payload).status_code == 401
    # 6th attempt (even with correct password) is throttled.
    res = client.post("/api/admin/login", json={
        "store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD,
    })
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


def test_successful_login_resets_failure_counter(client):
    bad = {"store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": "bad"}
    for _ in range(4):
        client.post("/api/admin/login", json=bad)
    # Success clears counter...
    ok = {"store_code": STORE_CODE, "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    assert client.post("/api/admin/login", json=ok).status_code == 200
    # ...so the next wrong attempt is 401, not an immediate lockout.
    assert client.post("/api/admin/login", json=bad).status_code == 401


def test_expired_token_rejected():
    token = jwt.encode(
        {"admin_id": 1, "store_id": 1, "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        "test-secret", algorithm="HS256",
    )
    try:
        auth_service.verify_token(token)
        assert False, "expected AppError"
    except Exception as exc:  # AppError(UNAUTHORIZED)
        assert getattr(exc, "code", None) is not None
        assert exc.code.value == "UNAUTHORIZED"
