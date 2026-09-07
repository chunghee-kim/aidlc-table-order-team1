// Menu feature API + types (U3/B). Wraps ApiClient endpoints from MenuRouter.
import { apiClient } from "../../shared/api/api-client";

export interface CategoryView {
  id: number;
  name: string;
  display_order: number;
}

export interface MenuView {
  id: number;
  name: string;
  price: number;
  description?: string | null;
  image_url?: string | null;
  category_id: number;
  display_order: number;
  is_available: boolean;
}

export interface MenuInput {
  name: string;
  price: number;
  description?: string | null;
  category_id: number;
  image_url?: string | null;
}

export const menuApi = {
  // Public (customer) — no auth header.
  listCategories: () => apiClient.get<CategoryView[]>("/api/categories", { auth: false }),
  listMenus: () => apiClient.get<MenuView[]>("/api/menus", { auth: false }),

  // Admin — ApiClient attaches the Bearer token.
  create: (data: MenuInput) => apiClient.post<MenuView>("/api/admin/menus", data),
  update: (id: number, data: MenuInput) => apiClient.put<MenuView>(`/api/admin/menus/${id}`, data),
  remove: (id: number) => apiClient.delete<void>(`/api/admin/menus/${id}`),
  reorder: (categoryId: number, orderedMenuIds: number[]) =>
    apiClient.patch<void>(`/api/admin/categories/${categoryId}/menu-order`, {
      ordered_menu_ids: orderedMenuIds,
    }),
};

export function formatPrice(price: number): string {
  return `${price.toLocaleString("ko-KR")}원`;
}
