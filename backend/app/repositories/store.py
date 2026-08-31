"""StoreRepo (U2/A). Interface frozen in Phase 0; concrete SQLAlchemy impl added by U2/A."""
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Store


class StoreRepo(Protocol):
    def find_by_code(self, store_code: str) -> Store | None: ...


class SqlStoreRepo:
    """Session-scoped concrete StoreRepo. Inject a request/service-scoped Session."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_code(self, store_code: str) -> Store | None:
        return self.db.query(Store).filter_by(store_code=store_code).one_or_none()
