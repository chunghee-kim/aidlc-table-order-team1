"""MenuRouter (U3/B) — public menu/category browsing + admin menu CRUD & ordering.

Endpoints (component-methods.md §3):
  GET    /api/menus                                       -> list_menus_for_customer  (public)
  GET    /api/categories                                  -> list_categories          (public)
  POST   /api/admin/menus                                 -> create_menu              (admin)
  PUT    /api/admin/menus/{menu_id}                       -> update_menu              (admin)
  DELETE /api/admin/menus/{menu_id}                       -> delete_menu              (admin)
  PATCH  /api/admin/categories/{category_id}/menu-order   -> reorder_menus            (admin)
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependency import AdminContext, get_current_admin
from app.db import get_db
from app.schemas.menu import CategoryView, MenuInput, MenuOrderInput, MenuView
from app.services.menu_service import MenuService

router = APIRouter(prefix="/api", tags=["menu"])


def _service(db: Session = Depends(get_db)) -> MenuService:
    return MenuService(db)


@router.get("/menus", response_model=list[MenuView])
def list_menus(svc: MenuService = Depends(_service)) -> list[MenuView]:
    return svc.list_menus_for_customer(svc.default_store_id())


@router.get("/categories", response_model=list[CategoryView])
def list_categories(svc: MenuService = Depends(_service)) -> list[CategoryView]:
    return svc.list_categories(svc.default_store_id())


@router.post("/admin/menus", response_model=MenuView, status_code=status.HTTP_201_CREATED)
def create_menu(
    data: MenuInput,
    admin: AdminContext = Depends(get_current_admin),
    svc: MenuService = Depends(_service),
) -> MenuView:
    return svc.create_menu(data, admin)


@router.put("/admin/menus/{menu_id}", response_model=MenuView)
def update_menu(
    menu_id: int,
    data: MenuInput,
    admin: AdminContext = Depends(get_current_admin),
    svc: MenuService = Depends(_service),
) -> MenuView:
    return svc.update_menu(menu_id, data, admin)


@router.delete("/admin/menus/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(
    menu_id: int,
    admin: AdminContext = Depends(get_current_admin),
    svc: MenuService = Depends(_service),
) -> None:
    svc.delete_menu(menu_id, admin)


@router.patch("/admin/categories/{category_id}/menu-order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_menus(
    category_id: int,
    body: MenuOrderInput,
    admin: AdminContext = Depends(get_current_admin),
    svc: MenuService = Depends(_service),
) -> None:
    svc.reorder_menus(category_id, body.ordered_menu_ids, admin)
