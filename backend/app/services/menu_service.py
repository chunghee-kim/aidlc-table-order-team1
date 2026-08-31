"""MenuService (U3/B) — customer menu browsing + admin menu CRUD/ordering.

Invariants (US-A-16, PBT 🔬): menu price > 0 and required fields (name, valid category).
Consumers: MenuRouter. `SqlMenuRepo.list_by_store` unit prices feed U4 order creation.
The service owns the DB transaction (commit); repositories only add/flush.
"""
from sqlalchemy.orm import Session

from app.auth.dependency import AdminContext
from app.errors import AppError, ErrorCode
from app.models import Menu, Store
from app.repositories.category import SqlCategoryRepo
from app.repositories.menu import SqlMenuRepo
from app.schemas.menu import CategoryView, MenuInput, MenuView

NAME_MAX = 100  # matches Menu.name column length


class MenuService:
    def __init__(self, db: Session):
        self.db = db
        self.menus = SqlMenuRepo(db)
        self.categories = SqlCategoryRepo(db)

    # ---- customer (public) ----
    def default_store_id(self) -> int | None:
        """Single-store MVP: resolve the sole store. Returns None on an unseeded DB."""
        store = self.db.query(Store).order_by(Store.id).first()
        return store.id if store else None

    def list_menus_for_customer(self, store_id: int | None) -> list[MenuView]:
        if store_id is None:
            return []
        return [_to_menu_view(m) for m in self.menus.list_by_store(store_id)]

    def list_categories(self, store_id: int | None) -> list[CategoryView]:
        if store_id is None:
            return []
        return [
            CategoryView(id=c.id, name=c.name, display_order=c.display_order)
            for c in self.categories.list_by_store(store_id)
        ]

    # ---- admin ----
    def create_menu(self, data: MenuInput, actor: AdminContext) -> MenuView:  # 🔬
        self._validate_input(data)
        self._require_category(data.category_id, actor.store_id)
        menu = self.menus.create(actor.store_id, data)
        self.db.commit()
        self.db.refresh(menu)
        return _to_menu_view(menu)

    def update_menu(self, menu_id: int, data: MenuInput, actor: AdminContext) -> MenuView:  # 🔬
        self._validate_input(data)
        self._require_owned_menu(self.menus.get(menu_id), actor.store_id)
        self._require_category(data.category_id, actor.store_id)
        menu = self.menus.update(menu_id, data)
        self.db.commit()
        self.db.refresh(menu)  # menu is non-None: ownership check above guarantees existence
        return _to_menu_view(menu)

    def delete_menu(self, menu_id: int, actor: AdminContext) -> None:
        self._require_owned_menu(self.menus.get(menu_id), actor.store_id)
        self.menus.delete(menu_id)
        self.db.commit()

    def reorder_menus(self, category_id: int, ordered_menu_ids: list[int], actor: AdminContext) -> None:
        self._require_category(category_id, actor.store_id)
        self.menus.update_order(category_id, ordered_menu_ids)
        self.db.commit()

    # ---- validation helpers ----
    def _validate_input(self, data: MenuInput) -> None:
        errors: dict[str, str] = {}
        if not data.name or not data.name.strip():
            errors["name"] = "메뉴명은 필수입니다."
        elif len(data.name.strip()) > NAME_MAX:
            errors["name"] = f"메뉴명은 {NAME_MAX}자 이하여야 합니다."
        if data.price <= 0:
            errors["price"] = "가격은 0보다 커야 합니다."
        if errors:
            raise AppError(ErrorCode.VALIDATION_ERROR, "메뉴 입력값이 유효하지 않습니다.", {"fields": errors})

    def _require_category(self, category_id: int, store_id: int) -> None:
        category = self.categories.get(category_id)
        if category is None or category.store_id != store_id:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "유효하지 않은 카테고리입니다.",
                {"fields": {"category_id": "존재하지 않는 카테고리입니다."}},
            )

    def _require_owned_menu(self, menu: Menu | None, store_id: int) -> None:
        if menu is None or menu.store_id != store_id:
            raise AppError(ErrorCode.NOT_FOUND, "메뉴를 찾을 수 없습니다.")


def _to_menu_view(menu: Menu) -> MenuView:
    return MenuView(
        id=menu.id,
        name=menu.name,
        price=menu.price,
        description=menu.description,
        image_url=menu.image_url,
        category_id=menu.category_id,
        display_order=menu.display_order,
        is_available=menu.is_available,
    )
