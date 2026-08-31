"""Menu / category schemas (U3/B consumes; frozen in Phase 0)."""
from pydantic import BaseModel


class CategoryView(BaseModel):
    id: int
    name: str
    display_order: int


class MenuView(BaseModel):
    id: int
    name: str
    price: int
    description: str | None = None
    image_url: str | None = None
    category_id: int
    display_order: int
    is_available: bool


class MenuInput(BaseModel):
    name: str
    price: int
    description: str | None = None
    category_id: int
    image_url: str | None = None


class MenuOrderInput(BaseModel):
    ordered_menu_ids: list[int]
