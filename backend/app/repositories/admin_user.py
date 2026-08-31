from typing import Protocol

from app.models import AdminUser


class AdminUserRepo(Protocol):
    def find_by_store_and_username(self, store_code: str, username: str) -> AdminUser | None: ...
