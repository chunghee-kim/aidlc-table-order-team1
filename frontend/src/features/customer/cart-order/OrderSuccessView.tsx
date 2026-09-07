// U4/C — OrderSuccessView: show order number, then auto-redirect to menu after 5s (US-C-13).
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const REDIRECT_SECONDS = 5;

export default function OrderSuccessView() {
  const navigate = useNavigate();
  const location = useLocation();
  const orderNumber = (location.state as { orderNumber?: string } | null)?.orderNumber ?? null;
  const [remaining, setRemaining] = useState(REDIRECT_SECONDS);

  useEffect(() => {
    const tick = setInterval(() => setRemaining((r) => Math.max(0, r - 1)), 1000);
    const redirect = setTimeout(() => navigate("/customer", { replace: true }), REDIRECT_SECONDS * 1000);
    return () => {
      clearInterval(tick);
      clearTimeout(redirect);
    };
  }, [navigate]);

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif", maxWidth: 520, margin: "0 auto", textAlign: "center" }}>
      <div style={{ fontSize: 56 }}>✅</div>
      <h1>주문이 접수되었습니다</h1>
      {orderNumber ? (
        <p style={{ fontSize: 20 }}>
          주문 번호: <strong>{orderNumber}</strong>
        </p>
      ) : (
        <p style={{ color: "#666" }}>주문이 정상적으로 접수되었습니다.</p>
      )}
      <p style={{ color: "#666" }}>{remaining}초 후 메뉴 화면으로 돌아갑니다.</p>
      <button
        style={{
          height: 48,
          padding: "0 24px",
          borderRadius: 8,
          border: "none",
          background: "#2563eb",
          color: "#fff",
          fontSize: 16,
          cursor: "pointer",
        }}
        onClick={() => navigate("/customer", { replace: true })}
      >
        메뉴로 지금 돌아가기
      </button>
    </main>
  );
}
