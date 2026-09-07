// TableLoginView (U2/A) — manual table login fallback when a tablet isn't yet configured.
// Saves the tablet config on success so subsequent visits auto-login (US-C-01/02).
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { saveTableConfig, useTableSession } from "../../../context/table-session-context";
import { ApiError } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";

export function TableLoginView() {
  const { bootstrap } = useTableSession();
  const navigate = useNavigate();
  const [storeCode, setStoreCode] = useState("STORE01");
  const [tableNumber, setTableNumber] = useState("");
  const [tablePassword, setTablePassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const num = Number(tableNumber);
    if (!Number.isInteger(num) || num < 1) {
      setError("테이블 번호는 1 이상의 정수여야 합니다.");
      return;
    }
    setSubmitting(true);
    try {
      saveTableConfig({ storeCode: storeCode.trim(), tableNumber: num, tablePassword });
      await bootstrap(); // validates against the server; throws on bad credentials
      navigate("/customer", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "테이블 로그인에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 360, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>테이블 로그인</h1>
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          매장 식별자
          <input value={storeCode} onChange={(e) => setStoreCode(e.target.value)} required
                 style={{ padding: 10, minHeight: 44 }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          테이블 번호
          <input type="number" min={1} value={tableNumber} onChange={(e) => setTableNumber(e.target.value)}
                 required style={{ padding: 10, minHeight: 44 }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          테이블 비밀번호
          <input type="password" value={tablePassword} onChange={(e) => setTablePassword(e.target.value)}
                 required style={{ padding: 10, minHeight: 44 }} />
        </label>
        {error && <p role="alert" style={{ color: "#c0392b", margin: 0 }}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "확인 중…" : "로그인"}
        </Button>
      </form>
    </main>
  );
}
