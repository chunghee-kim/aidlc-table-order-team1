from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Category


class CategoryRepo(Protocol):
    def list_by_store(self, store_id: int) -> list[Category]: ...


class SqlCategoryRepo:
    """SQLAlchemy CategoryRepo (U3/B)."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def list_by_store(self, store_id: int) -> list[Category]:
        return (
            self.db.query(Category)
            .filter(Category.store_id == store_id)
            .order_by(Category.display_order, Category.id)
            .all()
        )
