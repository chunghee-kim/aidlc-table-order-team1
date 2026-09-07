// U5/D — monitoring REST calls (built on the U1 ApiClient; admin JWT auto-attached).
import { apiClient } from "../../../shared/api/api-client";
import type { AdminOrder, TableTotals } from "./types";

export const monitoringApi = {
  /** Initial snapshot of active orders (US-A-05/08). */
  listOrders(table?: number | null): Promise<AdminOrder[]> {
    const q = table != null ? `?table=${table}` : "";
    return apiClient.get<AdminOrder[]>(`/api/admin/orders${q}`);
  },

  /** Transition an order's status (US-A-09). Grid converges via the order_updated SSE event. */
  changeStatus(orderId: number, status: string): Promise<AdminOrder> {
    return apiClient.patch<AdminOrder>(`/api/admin/orders/${orderId}/status`, { status });
  },

  /** Authoritative delete (US-A-10). Grid converges via the order_deleted SSE event. */
  deleteOrder(orderId: number): Promise<TableTotals> {
    return apiClient.delete<TableTotals>(`/api/admin/orders/${orderId}`);
  },
};
