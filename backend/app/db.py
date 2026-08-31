"""DbSessionProvider (U1) — engine, session factory, declarative Base, request-scoped session."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite single-file. check_same_thread=False so FastAPI's threadpool can share the engine.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: request-scoped DB session. Service methods own commit/rollback."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create all tables (create_all strategy, no Alembic). Import models for registration."""
    import app.models  # noqa: F401  (ensures all models are registered on Base.metadata)

    Base.metadata.create_all(bind=engine)
