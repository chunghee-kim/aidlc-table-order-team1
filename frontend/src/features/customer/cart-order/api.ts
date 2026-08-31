// U4/C — customer order API calls (built on the U1 ApiClient). Table-session scoped (no auth).
import { apiClient } from "../../../shared/api/api-client";

export interface OrderItemView {
  menu_name: string;
  unit_price: number;
  quantity: number;
}

export interface OrderView {
  order_number: string;
  table_id: number;
  session_id: number;
  items: OrderItemView[];
  total_amount: number;
  status: string; // 대기중 | 준비중 | 완료
  created_at: string;
}

export interface OrderPage {
  items: OrderView[];
  next_cursor: number | null;
}

export interface CreateOrderRequest {
  store_id: number;
  table_id: number;
  items: { menu_id: number; quantity: number }[];
}

export function createOrder(req: CreateOrderRequest): Promise<OrderView> {
  return apiClient.post<OrderView>("/api/orders", req, { auth: false });
}

export function fetchCurrentOrders(
  sessionId: number,
  cursor: number | null,
  limit = 20,
): Promise<OrderPage> {
  const params = new URLSearchParams({ session_id: String(sessionId), limit: String(limit) });
  if (cursor != null) params.set("cursor", String(cursor));
  return apiClient.get<OrderPage>(`/api/orders?${params.toString()}`, { auth: false });
}
