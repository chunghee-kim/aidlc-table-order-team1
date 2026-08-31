from typing import Protocol

from app.models import Category


class CategoryRepo(Protocol):
    def list_by_store(self, store_id: int) -> list[Category]: ...
