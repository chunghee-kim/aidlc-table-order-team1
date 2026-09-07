// U6 — 과거 내역 화면(admin 라우트 /admin/history, US-A-13~15).
// 필터바(테이블/날짜) → GET /api/admin/history → 시간 역순 카드. 시각은 로컬 변환 표시.
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, apiClient } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";
import { buildHistoryQuery } from "./query";
import type { OrderHistoryItem } from "./types";

function formatLocal(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function OrderHistoryView() {
  const navigate = useNavigate();
  const [tableText, setTableText] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [items, setItems] = useState<OrderHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const tableNum = Number(tableText);
    const query = buildHistoryQuery({
      table: tableText.trim() !== "" && Number.isInteger(tableNum) && tableNum > 0 ? tableNum : null,
      dateFrom: dateFrom || null,
      dateTo: dateTo || null,
    });
    try {
      const res = await apiClient.get<OrderHistoryItem[]>(`/api/admin/history${query}`);
      setItems(res);
      setLoaded(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "이력을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [tableText, dateFrom, dateTo]);

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif", maxWidth: 720 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>과거 주문 내역</h1>
        <Button onClick={() => navigate("/admin")} style={{ background: "#f2f2f2" }}>
          닫기
        </Button>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          alignItems: "flex-end",
          margin: "16px 0",
        }}
      >
        <label>
          테이블(선택)
          <input
            type="number"
            min={1}
            value={tableText}
            onChange={(e) => setTableText(e.target.value)}
            placeholder="전체"
            style={{ display: "block", marginTop: 4, padding: 8, width: 120 }}
          />
        </label>
        <label>
          시작일
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{ display: "block", marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          종료일
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{ display: "block", marginTop: 4, padding: 8 }}
          />
        </label>
        <Button onClick={load} disabled={loading}>
          {loading ? "조회 중…" : "조회"}
        </Button>
      </div>

      {loading && <p role="status">불러오는 중…</p>}
      {error && (
        <p role="alert" style={{ color: "#d9534f" }}>
          {error}
        </p>
      )}
      {!loading && !error && loaded && items.length === 0 && (
        <p style={{ color: "#666" }}>이력이 없습니다.</p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((h, i) => (
          <article
            key={`${h.order_number}-${h.closed_at}-${i}`}
            style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>주문번호 {h.order_number}</strong>
              <span style={{ color: "#666" }}>주문시각 {formatLocal(h.ordered_at)}</span>
            </div>
            <ul style={{ margin: "8px 0", paddingLeft: 20 }}>
              {h.items.map((it, idx) => (
                <li key={idx}>
                  {it.menu_name} × {it.quantity}
                  <span style={{ color: "#888" }}> (단가 {it.unit_price.toLocaleString()}원)</span>
                </li>
              ))}
            </ul>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>총액 {h.total_amount.toLocaleString()}원</strong>
              <span style={{ color: "#666" }}>이용완료 {formatLocal(h.closed_at)}</span>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
