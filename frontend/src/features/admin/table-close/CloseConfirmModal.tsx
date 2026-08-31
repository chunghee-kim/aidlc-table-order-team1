// U6 — 이용완료 확인 팝업 (US-A-12 "확인 팝업"). 확정 시 onConfirm 호출.
import { Button } from "../../../shared/ui/Button";

interface CloseConfirmModalProps {
  tableId: number;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function CloseConfirmModal({ tableId, loading, onConfirm, onCancel }: CloseConfirmModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          padding: 24,
          width: "min(90vw, 360px)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        }}
      >
        <h2 style={{ marginTop: 0 }}>이용 완료</h2>
        <p>
          테이블 <strong>{tableId}</strong> 을(를) 이용 완료 처리하시겠습니까? 진행 중인 주문은 과거
          내역으로 이관되고 테이블은 초기화됩니다.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 16 }}>
          <Button onClick={onCancel} disabled={loading} style={{ background: "#f2f2f2" }}>
            취소
          </Button>
          <Button
            onClick={onConfirm}
            disabled={loading}
            style={{ background: "#d9534f", color: "#fff", borderColor: "#d9534f" }}
          >
            {loading ? "처리 중…" : "이용 완료"}
          </Button>
        </div>
      </div>
    </div>
  );
}
