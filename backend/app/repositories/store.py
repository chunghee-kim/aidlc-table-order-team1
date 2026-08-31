from typing import Protocol

from app.models import Store


class StoreRepo(Protocol):
    def find_by_code(self, store_code: str) -> Store | None: ...
