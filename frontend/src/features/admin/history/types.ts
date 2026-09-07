// U6 — 과거 내역 (프론트 로컬 타입). 서버 OrderHistoryView 계약과 1:1.
export interface OrderItemView {
  menu_name: string;
  unit_price: number;
  quantity: number;
}

export interface OrderHistoryItem {
  order_number: string;
  items: OrderItemView[];
  total_amount: number;
  ordered_at: string; // 서버 UTC ISO-8601
  closed_at: string; // 서버 UTC ISO-8601
}
