"""Test fixtures for U2 (Auth & Session).

Point the app at a throwaway SQLite file BEFORE any app import so the module-level engine in
app.db binds to it. Each test module gets a freshly seeded store/admin/table.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_u2.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_EXPIRE_HOURS"] = "16"
os.environ["BCRYPT_COST"] = "4"  # fast hashing for tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

STORE_CODE = "STORE01"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1234"
TABLE_NUMBER = 5
TABLE_PASSWORD = "5"


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    """Recreate a clean schema + minimal seed once per test session."""
    db_path = "./test_u2.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.db import Base, SessionLocal, engine
    import app.models  # noqa: F401  (register all tables)
    from app.models import AdminUser, Store, Table
    from app.security import hash_password

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        store = Store(store_code=STORE_CODE, name="테스트 카페")
        db.add(store)
        db.flush()
        db.add(AdminUser(store_id=store.id, username=ADMIN_USERNAME,
                         password_hash=hash_password(ADMIN_PASSWORD)))
        db.add(Table(store_id=store.id, table_number=TABLE_NUMBER,
                     table_password_hash=hash_password(TABLE_PASSWORD), is_active=True))
        db.commit()
    finally:
        db.close()

    yield

    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(autouse=True)
def _reset_login_attempts():
    """Clear the in-memory login-attempt throttle between tests."""
    from app.services import auth_service

    auth_service._attempts.clear()
    yield
    auth_service._attempts.clear()


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
