// TableSetupView (U2/A) — tablet initial setup (US-A-04). saveSetup() -> POST /api/admin/tables/{id}/setup.
// On success, persists the tablet config locally so the customer app can auto-login (US-C-01).
import { useState, type FormEvent } from "react";
import { useAuth } from "../../../context/auth-context";
import { saveTableConfig } from "../../../context/table-session-context";
import { apiClient, ApiError } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";

interface TableSetupResponse {
  table_id: number;
  table_number: number;
  auto_login_enabled: boolean;
}

export function TableSetupView() {
  const { isAuthenticated } = useAuth();
  const [storeCode, setStoreCode] = useState("STORE01");
  const [tableNumber, setTableNumber] = useState("");
  const [tablePassword, setTablePassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function saveSetup(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const num = Number(tableNumber);
    if (!Number.isInteger(num) || num < 1) {
      setError("테이블 번호는 1 이상의 정수여야 합니다.");
      return;
    }
    setSubmitting(true);
    try {
      // The upsert is keyed by table_number; path id is a REST placeholder.
      const res = await apiClient.post<TableSetupResponse>(
        `/api/admin/tables/${num}/setup`,
        { table_number: num, table_password: tablePassword },
      );
      // Persist tablet config so this tablet auto-logs-in as a customer device.
      saveTableConfig({ storeCode: storeCode.trim(), tableNumber: res.table_number, tablePassword });
      setMessage(`테이블 ${res.table_number} 설정 완료 — 이 태블릿에서 자동 로그인이 활성화되었습니다.`);
      setTablePassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "설정에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!isAuthenticated()) {
    return (
      <main style={{ padding: 24, fontFamily: "sans-serif" }}>
        <h1>테이블 설정</h1>
        <p role="alert">관리자 로그인이 필요합니다. <a href="/admin/login">로그인</a></p>
      </main>
    );
  }

  return (
    <main style={{ padding: 24, maxWidth: 360, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>테이블 태블릿 설정</h1>
      <form onSubmit={saveSetup} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
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
        {message && <p style={{ color: "#27ae60", margin: 0 }}>{message}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "저장 중…" : "설정 저장"}
        </Button>
      </form>
    </main>
  );
}
