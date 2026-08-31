"""Shared test fixtures (U3/B). In-memory SQLite with the full schema + a seeded store/category."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.db import Base
from app.models import Category, Store


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
