// U6 — 이용완료 결과 (프론트 로컬 타입). 서버 CloseResponse 계약과 1:1.
export interface CloseResult {
  moved_order_count: number;
  closed_at: string; // 서버 UTC ISO-8601; 표시 변환은 프론트에서.
}
