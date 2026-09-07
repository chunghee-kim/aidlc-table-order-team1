// AutoLoginBootstrap (U2/A) — customer tablet auto-login (US-C-01/02).
// On entry: if the tablet is configured, resolve the table session and proceed to the menu;
// otherwise prompt for initial setup. Survives refresh (config lives in localStorage).
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTableSession } from "../../../context/table-session-context";
import { ApiError } from "../../../shared/api/api-client";

type Status = "checking" | "unconfigured" | "error";

export function AutoLoginBootstrap() {
  const { bootstrap, isConfigured } = useTableSession();
  const navigate = useNavigate();
  const [status, setStatus] = useState<Status>("checking");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!isConfigured()) {
        if (!cancelled) setStatus("unconfigured");
        return;
      }
      try {
        await bootstrap();
        if (!cancelled) navigate("/customer", { replace: true });
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "자동 로그인에 실패했습니다.");
        setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [bootstrap, isConfigured, navigate]);

  if (status === "checking") {
    return <main style={{ padding: 24, fontFamily: "sans-serif" }}><p>자동 로그인 중…</p></main>;
  }

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>초기 설정이 필요합니다</h1>
      {status === "error" && <p role="alert" style={{ color: "#c0392b" }}>{error}</p>}
      <p>이 태블릿은 아직 테이블에 연결되지 않았습니다.</p>
      <p>
        <Link to="/customer/table-login">테이블 로그인</Link>
        {" · "}
        <Link to="/admin/table-setup">관리자 설정</Link>
      </p>
    </main>
  );
}
