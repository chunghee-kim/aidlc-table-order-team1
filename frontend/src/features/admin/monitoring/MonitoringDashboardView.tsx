// U5/D — MonitoringDashboardView (US-A-05/06/07/09/10). Entry point: REST snapshot for fast first
// paint + SSE subscription for realtime. Owns the order map / unseen set / selection; the reducer
// patches on incremental events and fully replaces on the snapshot frame (reconnect recovery).
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../context/auth-context";
import { ApiError } from "../../../shared/api/api-client";
import type { SseEvent } from "../../../shared/api/sse-client";
import { monitoringApi } from "./api";
import { OrderDetailModal } from "./OrderDetailModal";
import { TableCard } from "./TableCard";
import { TableFilterBar } from "./TableFilterBar";
import type { AdminOrder, OrderFrame } from "./types";
import { useOrderStream } from "./useOrderStream";

const CONN_LABEL: Record<string, { text: string; color: string }> = {
  connecting: { text: "연결 중…", color: "#a16207" },
  open: { text: "실시간 연결됨", color: "#15803d" },
  reconnecting: { text: "재연결 중…", color: "#b91c1c" },
};

export function MonitoringDashboardView() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [ordersById, setOrdersById] = useState<Map<number, AdminOrder>>(new Map());
  const [unseen, setUnseen] = useState<Set<number>>(new Set());
  const [filterTableId, setFilterTableId] = useState<number | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Not logged in -> send to login (SSE/REST would 401 anyway).
  useEffect(() => {
    if (!isAuthenticated()) navigate("/admin/login");
  }, [isAuthenticated, navigate]);

  // Fast first paint from REST; the SSE snapshot then replaces this authoritatively.
  useEffect(() => {
    let cancelled = false;
    monitoringApi
      .listOrders()
      .then((orders) => {
        if (cancelled) return;
        setOrdersById(new Map(orders.map((o) => [o.order_id, o])));
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "주문을 불러오지 못했습니다.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onEvent = useCallback((event: SseEvent) => {
    const frame = event.payload as OrderFrame;
    switch (frame.type) {
      case "snapshot": {
        const next = new Map(frame.orders.map((o) => [o.order_id, o]));
        setOrdersById(next);
        // Keep unseen only for orders still present (drop deleted/migrated); Q7-B.
        setUnseen((prev) => new Set([...prev].filter((id) => next.has(id))));
        break;
      }
      case "order_created": {
        const o = frame.order;
        setOrdersById((prev) => new Map(prev).set(o.order_id, o));
        setUnseen((prev) => new Set(prev).add(o.order_id));
        break;
      }
      case "order_updated": {
        const o = frame.order;
        setOrdersById((prev) => {
          const next = new Map(prev);
          next.set(o.order_id, o); // replace (status badge refresh)
          return next;
        });
        break;
      }
      case "order_deleted": {
        setOrdersById((prev) => {
          const next = new Map(prev);
          next.delete(frame.order_id);
          return next;
        });
        setUnseen((prev) => {
          if (!prev.has(frame.order_id)) return prev;
          const next = new Set(prev);
          next.delete(frame.order_id);
          return next;
        });
        break;
      }
    }
  }, []);

  const { connState } = useOrderStream(onEvent);

  const openDetail = useCallback((orderId: number) => {
    setSelectedOrderId(orderId);
    setUnseen((prev) => {
      if (!prev.has(orderId)) return prev;
      const next = new Set(prev);
      next.delete(orderId); // 열람 처리 (Q7-B): 강조 해제
      return next;
    });
  }, []);

  const allOrders = useMemo(() => [...ordersById.values()], [ordersById]);
  const tables = useMemo(
    () => [...new Set(allOrders.map((o) => o.table_id))].sort((a, b) => a - b),
    [allOrders],
  );

  // Group visible orders by table, newest-first, with per-table total.
  const cards = useMemo(() => {
    const visible = filterTableId == null ? allOrders : allOrders.filter((o) => o.table_id === filterTableId);
    const byTable = new Map<number, AdminOrder[]>();
    for (const o of visible) {
      const arr = byTable.get(o.table_id) ?? [];
      arr.push(o);
      byTable.set(o.table_id, arr);
    }
    return [...byTable.entries()]
      .map(([tableId, orders]) => {
        orders.sort((a, b) => (a.created_at < b.created_at ? 1 : -1)); // newest first
        return { tableId, orders, total: orders.reduce((s, o) => s + o.total_amount, 0) };
      })
      .sort((a, b) => a.tableId - b.tableId);
  }, [allOrders, filterTableId]);

  const selectedOrder = selectedOrderId != null ? ordersById.get(selectedOrderId) ?? null : null;
  const conn = CONN_LABEL[connState];

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0 }}>주문 모니터링</h1>
        <span style={{ color: conn.color, fontSize: 13, fontWeight: 600 }}>● {conn.text}</span>
        <span style={{ marginLeft: "auto", color: "#666", fontSize: 13 }}>활성 주문 {allOrders.length}건</span>
      </div>

      {loadError && <p style={{ color: "#b91c1c" }}>{loadError}</p>}

      <TableFilterBar tables={tables} active={filterTableId} onSelect={setFilterTableId} />

      {cards.length === 0 ? (
        <p style={{ color: "#888", marginTop: 24 }}>표시할 활성 주문이 없습니다. 고객이 주문하면 실시간으로 나타납니다.</p>
      ) : (
        <div
          style={{
            display: "grid",
            gap: 14,
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            marginTop: 8,
          }}
        >
          {cards.map((c) => (
            <TableCard
              key={c.tableId}
              tableId={c.tableId}
              total={c.total}
              orders={c.orders}
              unseen={unseen}
              onOpen={openDetail}
            />
          ))}
        </div>
      )}

      {selectedOrder && <OrderDetailModal order={selectedOrder} onClose={() => setSelectedOrderId(null)} />}
    </main>
  );
}
