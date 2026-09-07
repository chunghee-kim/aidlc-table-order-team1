// U6 — 독립 admin 라우트 /admin/table-close. U5/D 대시보드 미구축 상황의 시연용 진입점.
// 테이블 번호(=table_id) 입력 → 이용 완료 버튼 → 확인 모달 → 성공 시 토스트.
import { useState } from "react";

import { Button } from "../../../shared/ui/Button";
import { CloseConfirmModal } from "./CloseConfirmModal";
import { useCloseTable } from "./useCloseTable";

export function CloseTableView() {
  const [tableIdText, setTableIdText] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const { loading, error, closeTable } = useCloseTable();

  const tableId = Number(tableIdText);
  const valid = tableIdText.trim() !== "" && Number.isInteger(tableId) && tableId > 0;

  async function handleConfirm() {
    try {
      const result = await closeTable(tableId);
      setConfirming(false);
      setToast(`이관 ${result.moved_order_count}건 · 리셋 완료`);
    } catch {
      // 에러는 훅 상태(error)로 표시.
      setConfirming(false);
    }
  }

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif", maxWidth: 480 }}>
      <h1>이용 완료</h1>
      <p style={{ color: "#666" }}>테이블 번호를 입력하고 이용 완료 처리를 진행합니다.</p>

      <label style={{ display: "block", marginBottom: 8 }}>
        테이블 번호
        <input
          type="number"
          min={1}
          value={tableIdText}
          onChange={(e) => {
            setTableIdText(e.target.value);
            setToast(null);
          }}
          style={{ display: "block", marginTop: 4, padding: 8, width: "100%", boxSizing: "border-box" }}
        />
      </label>

      <Button onClick={() => setConfirming(true)} disabled={!valid || loading}>
        이용 완료 처리
      </Button>

      {toast && (
        <p role="status" style={{ marginTop: 16, color: "#2e7d32" }}>
          ✅ {toast}
        </p>
      )}
      {error && (
        <p role="alert" style={{ marginTop: 16, color: "#d9534f" }}>
          {error.message}
        </p>
      )}

      {confirming && (
        <CloseConfirmModal
          tableId={tableId}
          loading={loading}
          onConfirm={handleConfirm}
          onCancel={() => setConfirming(false)}
        />
      )}
    </main>
  );
}
