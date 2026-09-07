// U5/D — TableCard: table number, active total, latest-3 preview, unseen highlight (US-A-05/06).
import type { CSSProperties } from "react";

import type { AdminOrder } from "./types";

const KRW = new Intl.NumberFormat("ko-KR");

const STATUS_COLOR: Record<string, string> = {
  대기중: "#a16207",
  준비중: "#1d4ed8",
  완료: "#15803d",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      style={{
        fontSize: 12,
        fontWeight: 600,
        color: STATUS_COLOR[status] ?? "#555",
        border: `1px solid ${STATUS_COLOR[status] ?? "#999"}`,
        borderRadius: 999,
        padding: "1px 8px",
        whiteSpace: "nowrap",
      }}
    >
      {status}
    </span>
  );
}

export function TableCard({
  tableId,
  total,
  orders,
  unseen,
  onOpen,
}: {
  tableId: number;
  total: number;
  orders: AdminOrder[]; // already sorted newest-first
  unseen: Set<number>;
  onOpen: (orderId: number) => void;
}) {
  const previews = orders.slice(0, 3);
  const hasUnseen = orders.some((o) => unseen.has(o.order_id));

  const cardStyle: CSSProperties = {
    border: hasUnseen ? "2px solid #f59e0b" : "1px solid #ddd",
    boxShadow: hasUnseen ? "0 0 0 3px rgba(245,158,11,0.18)" : "0 1px 2px rgba(0,0,0,0.04)",
    borderRadius: 12,
    padding: 16,
    background: "#fff",
    minWidth: 240,
  };

  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={{ fontSize: 18, fontWeight: 700 }}>
          {tableId}번 테이블
          {hasUnseen && <span style={{ color: "#f59e0b", marginLeft: 6, fontSize: 13 }}>● 신규</span>}
        </div>
        <div style={{ color: "#111", fontWeight: 700 }}>{KRW.format(total)}원</div>
      </div>
      <div style={{ color: "#888", fontSize: 12, margin: "4px 0 10px" }}>
        주문 {orders.length}건
      </div>

      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 6 }}>
        {previews.map((o) => {
          const lead = o.items[0];
          const more = o.items.length > 1 ? ` 외 ${o.items.length - 1}` : "";
          const isUnseen = unseen.has(o.order_id);
          return (
            <li key={o.order_id}>
              <button
                onClick={() => onOpen(o.order_id)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  minHeight: 44,
                  padding: "8px 10px",
                  borderRadius: 8,
                  border: "1px solid #eee",
                  background: isUnseen ? "#fffbeb" : "#fafafa",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <span style={{ color: "#999", marginRight: 6 }}>#{o.order_number.split("-").pop()}</span>
                  {lead ? `${lead.menu_name}${more}` : "(빈 주문)"}
                </span>
                <StatusBadge status={o.status} />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
