from typing import Protocol

from app.models import Menu
from app.schemas.menu import MenuInput


class MenuRepo(Protocol):
    """Menu data access. `list_by_store` is the unit-price source of truth consumed by U4 order creation."""

    def list_by_store(self, store_id: int) -> list[Menu]: ...

    def create(self, store_id: int, data: MenuInput) -> Menu: ...

    def update(self, menu_id: int, data: MenuInput) -> Menu | None: ...

    def delete(self, menu_id: int) -> None: ...

    def update_order(self, category_id: int, ordered_ids: list[int]) -> None: ...
