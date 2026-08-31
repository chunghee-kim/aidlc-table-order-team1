// AdminLoginView (U2/A) — admin login form (US-A-01). submitLogin() -> AuthContext.login.
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../context/auth-context";
import { ApiError } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";

export function AdminLoginView() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [storeCode, setStoreCode] = useState("STORE01");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submitLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(storeCode.trim(), username.trim(), password);
      navigate("/admin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 360, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>관리자 로그인</h1>
      <form onSubmit={submitLogin} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          매장 식별자
          <input value={storeCode} onChange={(e) => setStoreCode(e.target.value)} required
                 style={{ padding: 10, minHeight: 44 }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          사용자명
          <input value={username} onChange={(e) => setUsername(e.target.value)} required
                 autoComplete="username" style={{ padding: 10, minHeight: 44 }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          비밀번호
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                 autoComplete="current-password" style={{ padding: 10, minHeight: 44 }} />
        </label>
        {error && <p role="alert" style={{ color: "#c0392b", margin: 0 }}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "로그인 중…" : "로그인"}
        </Button>
      </form>
    </main>
  );
}
