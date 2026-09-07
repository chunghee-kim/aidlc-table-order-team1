// U5/D — OrderDetailModal (US-A-07/09/10): full items, status transition (allowed-only), delete.
// The grid converges via SSE events, so handlers don't setState the order themselves.
import { useState } from "react";

import { ApiError } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";
import { monitoringApi } from "./api";
import type { AdminOrder } from "./types";
import { NEXT_STATUS } from "./types";

const KRW = new Intl.NumberFormat("ko-KR");
const fmt = (iso: string) => new Date(iso).toLocaleString("ko-KR");

export function OrderDetailModal({ order, onClose }: { order: AdminOrder; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const next = NEXT_STATUS[order.status];

  async function run(fn: () => Promise<unknown>, closeAfter: boolean) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      if (closeAfter) onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "요청에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ background: "#fff", borderRadius: 12, padding: 20, width: 420, maxWidth: "100%", maxHeight: "90vh", overflow: "auto" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>
            {order.table_id}번 · 주문 {order.order_number}
          </h2>
          <button onClick={onClose} style={{ border: "none", background: "none", fontSize: 22, cursor: "pointer", lineHeight: 1 }}>
            ×
          </button>
        </div>
        <div style={{ color: "#888", fontSize: 12, marginTop: 4 }}>
          {fmt(order.created_at)} · 현재 상태 <b style={{ color: "#333" }}>{order.status}</b>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", margin: "14px 0" }}>
          <tbody>
            {order.items.map((it, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #f0f0f0" }}>
                <td style={{ padding: "6px 0" }}>{it.menu_name}</td>
                <td style={{ padding: "6px 0", textAlign: "right", color: "#666" }}>
                  {KRW.format(it.unit_price)}원 × {it.quantity}
                </td>
                <td style={{ padding: "6px 0", textAlign: "right", fontWeight: 600 }}>
                  {KRW.format(it.unit_price * it.quantity)}원
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ textAlign: "right", fontWeight: 700, fontSize: 16 }}>합계 {KRW.format(order.total_amount)}원</div>

        {error && <p style={{ color: "#b91c1c", fontSize: 13 }}>{error}</p>}

        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          {next && (
            <Button
              disabled={busy}
              onClick={() => run(() => monitoringApi.changeStatus(order.order_id, next), true)}
              style={{ background: "#1d4ed8", color: "#fff", borderColor: "#1d4ed8", flex: 1 }}
            >
              {next}(으)로 변경
            </Button>
          )}
          {!next && <div style={{ flex: 1, color: "#15803d", alignSelf: "center" }}>완료된 주문입니다.</div>}

          {!confirmDelete ? (
            <Button disabled={busy} onClick={() => setConfirmDelete(true)} style={{ color: "#b91c1c", borderColor: "#f0b0b0" }}>
              삭제
            </Button>
          ) : (
            <Button
              disabled={busy}
              onClick={() => run(() => monitoringApi.deleteOrder(order.order_id), true)}
              style={{ background: "#b91c1c", color: "#fff", borderColor: "#b91c1c" }}
            >
              정말 삭제
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
