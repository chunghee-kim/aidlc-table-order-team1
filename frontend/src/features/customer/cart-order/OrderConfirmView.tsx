// U4/C — OrderConfirmView: final review + confirm -> POST /api/orders (US-C-12).
// Empty cart is blocked; server total must equal cart total. On error, cart is preserved.
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCart } from "../../../context/cart-context";
import { useTableSession } from "../../../context/table-session-context";
import { ApiError } from "../../../shared/api/api-client";
import { createOrder } from "./api";

const KRW = new Intl.NumberFormat("ko-KR");

export default function OrderConfirmView() {
  const cart = useCart();
  const session = useTableSession();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const items = cart.getItems();
  const ctx = session.getContext();

  if (items.length === 0) {
    return (
      <main style={wrap}>
        <h1>주문 확인</h1>
        <p style={{ color: "#666" }}>장바구니가 비어 있습니다. 메뉴를 먼저 담아주세요.</p>
        <button style={secondaryBtn} onClick={() => navigate("/customer")}>
          메뉴로 돌아가기
        </button>
      </main>
    );
  }

  async function confirm() {
    if (!ctx) {
      setError("테이블 세션 정보가 없습니다. 태블릿 설정을 확인해주세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const order = await createOrder({
        store_id: ctx.storeId,
        table_id: ctx.tableId,
        items: items.map((i) => ({ menu_id: i.menuId, quantity: i.quantity })),
      });
      cart.clear(); // success -> empty cart (US-C-13)
      navigate("/customer/order/success", { state: { orderNumber: order.order_number } });
    } catch (e) {
      // Failure: show message, keep cart intact (US-C-13).
      setError(e instanceof ApiError ? e.message : "주문 생성에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={wrap}>
      <h1>주문 확인</h1>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #333" }}>
            <th style={{ padding: 8 }}>메뉴</th>
            <th style={{ padding: 8, textAlign: "right" }}>단가</th>
            <th style={{ padding: 8, textAlign: "center" }}>수량</th>
            <th style={{ padding: 8, textAlign: "right" }}>금액</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.menuId} style={{ borderBottom: "1px solid #eee" }}>
              <td style={{ padding: 8 }}>{it.name}</td>
              <td style={{ padding: 8, textAlign: "right" }}>{KRW.format(it.unitPrice)}원</td>
              <td style={{ padding: 8, textAlign: "center" }}>{it.quantity}</td>
              <td style={{ padding: 8, textAlign: "right" }}>{KRW.format(it.unitPrice * it.quantity)}원</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20, fontSize: 18, fontWeight: 700 }}>
        <span>총 금액</span>
        <span>{KRW.format(cart.getTotal())}원</span>
      </div>

      {error && (
        <p role="alert" style={{ color: "#b00", marginTop: 16 }}>
          {error}
        </p>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button style={secondaryBtn} disabled={submitting} onClick={() => navigate("/customer/cart")}>
          장바구니로
        </button>
        <button style={primaryBtn} disabled={submitting} onClick={confirm}>
          {submitting ? "주문 처리 중…" : "주문 확정"}
        </button>
      </div>
    </main>
  );
}

const wrap: React.CSSProperties = { padding: 24, fontFamily: "sans-serif", maxWidth: 640, margin: "0 auto" };
const primaryBtn: React.CSSProperties = {
  flex: 1,
  height: 48,
  borderRadius: 8,
  border: "none",
  background: "#2563eb",
  color: "#fff",
  fontSize: 16,
  fontWeight: 600,
  cursor: "pointer",
};
const secondaryBtn: React.CSSProperties = {
  flex: 1,
  height: 48,
  borderRadius: 8,
  border: "1px solid #ccc",
  background: "#fff",
  fontSize: 16,
  cursor: "pointer",
};
