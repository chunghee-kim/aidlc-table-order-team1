// U4/C — CurrentOrdersView: current session's orders, time order, infinite scroll (US-C-14).
// Only the active session's orders are shown (closed/previous sessions excluded server-side).
import { useCallback, useEffect, useRef, useState } from "react";

import { useTableSession } from "../../../context/table-session-context";
import { ApiError } from "../../../shared/api/api-client";
import { fetchCurrentOrders, type OrderView } from "./api";

const KRW = new Intl.NumberFormat("ko-KR");
const fmtTime = (iso: string) => new Date(iso).toLocaleString("ko-KR");

const STATUS_COLOR: Record<string, string> = {
  대기중: "#a16207",
  준비중: "#1d4ed8",
  완료: "#15803d",
};

export default function CurrentOrdersView() {
  const session = useTableSession();
  const sessionId = session.getContext()?.sessionId ?? null;

  const [orders, setOrders] = useState<OrderView[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinel = useRef<HTMLDivElement | null>(null);

  const loadMore = useCallback(async () => {
    if (sessionId == null || loading || !hasMore) return;
    setLoading(true);
    setError(null);
    try {
      const page = await fetchCurrentOrders(sessionId, cursor);
      setOrders((prev) => [...prev, ...page.items]);
      setCursor(page.next_cursor);
      setHasMore(page.next_cursor != null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "주문 내역을 불러오지 못했습니다.");
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  }, [sessionId, cursor, loading, hasMore]);

  // Initial load when a session is available.
  useEffect(() => {
    if (sessionId != null) loadMore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Infinite scroll: observe the sentinel and load the next page when it enters view.
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const obs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) loadMore();
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  if (sessionId == null) {
    return (
      <main style={wrap}>
        <h1>주문 내역</h1>
        <p style={{ color: "#666" }}>아직 진행 중인 세션이 없습니다. 첫 주문을 하면 내역이 표시됩니다.</p>
      </main>
    );
  }

  return (
    <main style={wrap}>
      <h1>주문 내역</h1>
      {orders.length === 0 && !loading && !error && <p style={{ color: "#666" }}>주문 내역이 없습니다.</p>}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {orders.map((o) => (
          <li key={o.order_number} style={{ border: "1px solid #eee", borderRadius: 10, padding: 16, marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{o.order_number}</strong>
              <span style={{ color: STATUS_COLOR[o.status] ?? "#333", fontWeight: 600 }}>{o.status}</span>
            </div>
            <div style={{ color: "#888", fontSize: 13, margin: "4px 0 12px" }}>{fmtTime(o.created_at)}</div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {o.items.map((it, idx) => (
                <li key={idx} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
                  <span>
                    {it.menu_name} × {it.quantity}
                  </span>
                  <span>{KRW.format(it.unit_price * it.quantity)}원</span>
                </li>
              ))}
            </ul>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontWeight: 700 }}>
              <span>합계</span>
              <span>{KRW.format(o.total_amount)}원</span>
            </div>
          </li>
        ))}
      </ul>

      {error && (
        <p role="alert" style={{ color: "#b00" }}>
          {error}
        </p>
      )}
      {loading && <p style={{ color: "#666" }}>불러오는 중…</p>}
      <div ref={sentinel} style={{ height: 1 }} />
    </main>
  );
}

const wrap: React.CSSProperties = { padding: 24, fontFamily: "sans-serif", maxWidth: 640, margin: "0 auto" };
