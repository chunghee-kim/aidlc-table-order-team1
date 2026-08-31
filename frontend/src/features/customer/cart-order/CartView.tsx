// U4/C — CartView: review cart, adjust quantity, remove, clear, proceed to confirm (US-C-08/09/10).
import { useNavigate } from "react-router-dom";

import { useCart } from "../../../context/cart-context";

const KRW = new Intl.NumberFormat("ko-KR");

export default function CartView() {
  const cart = useCart();
  const navigate = useNavigate();
  const items = cart.getItems();
  const empty = items.length === 0;

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif", maxWidth: 640, margin: "0 auto" }}>
      <h1>장바구니</h1>

      {empty ? (
        <p style={{ color: "#666" }}>장바구니가 비어 있습니다. 메뉴에서 항목을 담아주세요.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {items.map((it) => (
            <li
              key={it.menuId}
              style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0", borderBottom: "1px solid #eee" }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{it.name}</div>
                <div style={{ color: "#666", fontSize: 14 }}>{KRW.format(it.unitPrice)}원</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button
                  aria-label={`${it.name} 수량 감소`}
                  style={qtyBtn}
                  onClick={() => cart.setQuantity(it.menuId, it.quantity - 1)}
                >
                  −
                </button>
                <span style={{ minWidth: 24, textAlign: "center" }}>{it.quantity}</span>
                <button
                  aria-label={`${it.name} 수량 증가`}
                  style={qtyBtn}
                  onClick={() => cart.setQuantity(it.menuId, it.quantity + 1)}
                >
                  +
                </button>
              </div>
              <div style={{ minWidth: 90, textAlign: "right", fontWeight: 600 }}>
                {KRW.format(it.unitPrice * it.quantity)}원
              </div>
              <button aria-label={`${it.name} 삭제`} style={removeBtn} onClick={() => cart.removeItem(it.menuId)}>
                삭제
              </button>
            </li>
          ))}
        </ul>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24, fontSize: 18, fontWeight: 700 }}>
        <span>총 금액</span>
        <span>{KRW.format(cart.getTotal())}원</span>
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button style={secondaryBtn} disabled={empty} onClick={() => cart.clear()}>
          장바구니 비우기
        </button>
        <button style={primaryBtn} disabled={empty} onClick={() => navigate("/customer/order/confirm")}>
          주문하기
        </button>
      </div>
    </main>
  );
}

const qtyBtn: React.CSSProperties = {
  width: 44,
  height: 44,
  fontSize: 20,
  borderRadius: 8,
  border: "1px solid #ccc",
  background: "#fff",
  cursor: "pointer",
};
const removeBtn: React.CSSProperties = {
  height: 44,
  padding: "0 12px",
  borderRadius: 8,
  border: "1px solid #e0b4b4",
  background: "#fff",
  color: "#b00",
  cursor: "pointer",
};
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
