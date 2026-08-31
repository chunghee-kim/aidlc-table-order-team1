from typing import Protocol

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Category, Menu
from app.schemas.menu import MenuInput


class MenuRepo(Protocol):
    """Menu data access. `list_by_store` is the unit-price source of truth consumed by U4 order creation."""

    def list_by_store(self, store_id: int) -> list[Menu]: ...

    def create(self, store_id: int, data: MenuInput) -> Menu: ...

    def update(self, menu_id: int, data: MenuInput) -> Menu | None: ...

    def delete(self, menu_id: int) -> None: ...

    def update_order(self, category_id: int, ordered_ids: list[int]) -> None: ...


class SqlMenuRepo:
    """SQLAlchemy MenuRepo (U3/B). Flushes but never commits — MenuService owns the transaction."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, menu_id: int) -> Menu | None:
        return self.db.get(Menu, menu_id)

    def list_by_store(self, store_id: int) -> list[Menu]:
        # Customer-facing order: category display_order, then menu display_order, then id (stable tiebreak).
        return (
            self.db.query(Menu)
            .join(Category, Menu.category_id == Category.id)
            .filter(Menu.store_id == store_id)
            .order_by(Category.display_order, Menu.display_order, Menu.id)
            .all()
        )

    def create(self, store_id: int, data: MenuInput) -> Menu:
        # Append to the end of its category's current ordering.
        max_order = (
            self.db.query(func.coalesce(func.max(Menu.display_order), -1))
            .filter(Menu.store_id == store_id, Menu.category_id == data.category_id)
            .scalar()
        )
        menu = Menu(
            store_id=store_id,
            category_id=data.category_id,
            name=data.name,
            price=data.price,
            description=data.description,
            image_url=data.image_url,
            display_order=int(max_order) + 1,
        )
        self.db.add(menu)
        self.db.flush()
        return menu

    def update(self, menu_id: int, data: MenuInput) -> Menu | None:
        menu = self.db.get(Menu, menu_id)
        if menu is None:
            return None
        menu.name = data.name
        menu.price = data.price
        menu.description = data.description
        menu.category_id = data.category_id
        menu.image_url = data.image_url
        self.db.flush()
        return menu

    def delete(self, menu_id: int) -> None:
        # Physical delete allowed: OrderItem holds name/price snapshots (business-rules.md §3).
        menu = self.db.get(Menu, menu_id)
        if menu is not None:
            self.db.delete(menu)
            self.db.flush()

    def update_order(self, category_id: int, ordered_ids: list[int]) -> None:
        # display_order = position in the provided list; ignores ids outside this category.
        for position, menu_id in enumerate(ordered_ids):
            menu = self.db.get(Menu, menu_id)
            if menu is not None and menu.category_id == category_id:
                menu.display_order = position
        self.db.flush()
