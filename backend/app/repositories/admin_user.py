"""AdminUserRepo (U2/A). Interface frozen in Phase 0; concrete SQLAlchemy impl added by U2/A."""
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import AdminUser, Store


class AdminUserRepo(Protocol):
    def find_by_store_and_username(self, store_code: str, username: str) -> AdminUser | None: ...


class SqlAdminUserRepo:
    """Session-scoped concrete AdminUserRepo."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_store_and_username(self, store_code: str, username: str) -> AdminUser | None:
        return (
            self.db.query(AdminUser)
            .join(Store, AdminUser.store_id == Store.id)
            .filter(Store.store_code == store_code, AdminUser.username == username)
            .one_or_none()
        )
