"""Shared test fixtures.

U2 (Auth & Session): points the app at a throwaway SQLite file BEFORE any app import so the
module-level engine in app.db binds to it; exposes a seeded ``client`` fixture.

U3 (Menu): in-memory SQLite with the full schema + seeded store/category; exposes
``db_session``/``store``/``category`` fixtures.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_u2.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_EXPIRE_HOURS"] = "16"
os.environ["BCRYPT_COST"] = "4"  # fast hashing for tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  (register all models on Base.metadata)
from app.db import Base  # noqa: E402
from app.models import Category, Store  # noqa: E402

STORE_CODE = "STORE01"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1234"
TABLE_NUMBER = 5
TABLE_PASSWORD = "5"


# --- U2 (Auth & Session) fixtures ---
@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    """Recreate a clean schema + minimal seed once per test session."""
    db_path = "./test_u2.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.db import SessionLocal, engine
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


# --- U3 (Menu) fixtures ---
@pytest.fixture()
def db_session() -> Session:
    # StaticPool keeps one shared connection so the in-memory DB survives across sessions.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def store(db_session: Session) -> Store:
    s = Store(store_code="TEST01", name="테스트 매장")
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture()
def category(db_session: Session, store: Store) -> Category:
    c = Category(store_id=store.id, name="커피", display_order=0)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c
