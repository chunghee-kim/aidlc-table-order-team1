// U6 — 과거 내역 조회 쿼리스트링 빌더 (순수 함수, fast-check PBT 대상).
// 설정된 필터만 포함하고, 아무 것도 없으면 빈 문자열(선행 '?' 없음)을 반환한다.

export interface HistoryFilter {
  table?: number | null;
  dateFrom?: string | null; // "YYYY-MM-DD"
  dateTo?: string | null; // "YYYY-MM-DD"
}

export function buildHistoryQuery(filter: HistoryFilter): string {
  const params = new URLSearchParams();
  if (filter.table != null) params.set("table", String(filter.table));
  if (filter.dateFrom) params.set("date_from", filter.dateFrom);
  if (filter.dateTo) params.set("date_to", filter.dateTo);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
