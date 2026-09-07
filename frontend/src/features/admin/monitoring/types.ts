// U5/D — monitoring types. `AdminOrder` mirrors the backend AdminOrderView (OrderView + order_id).

export interface AdminOrderItem {
  menu_name: string;
  unit_price: number;
  quantity: number;
}

export interface AdminOrder {
  order_id: number;
  order_number: string;
  table_id: number;
  session_id: number;
  items: AdminOrderItem[];
  total_amount: number;
  status: string; // 대기중 | 준비중 | 완료
  created_at: string;
}

export interface TableTotals {
  table_id: number;
  total_amount: number;
}

// SSE frame shapes (the SseEvent.payload the reducer narrows over).
export type OrderFrame =
  | { type: "snapshot"; orders: AdminOrder[] }
  | { type: "order_created"; order: AdminOrder }
  | { type: "order_updated"; order: AdminOrder }
  | { type: "order_deleted"; order_id: number; table_id: number; table_total: number };

export const STATUS_ORDER: Record<string, number> = { 대기중: 0, 준비중: 1, 완료: 2 };
export const NEXT_STATUS: Record<string, string | null> = { 대기중: "준비중", 준비중: "완료", 완료: null };
