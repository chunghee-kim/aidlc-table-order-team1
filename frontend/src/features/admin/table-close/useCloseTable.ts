// U6 — 이용완료 훅. 확인 후 POST /api/admin/tables/{tableId}/close 호출.
// U5/D 대시보드가 이 훅을 import 해 테이블 카드 "이용 완료" 버튼에 연결(통합 시).
import { useCallback, useState } from "react";

import { ApiError, apiClient } from "../../../shared/api/api-client";
import type { CloseResult } from "./types";

interface CloseTableState {
  loading: boolean;
  error: ApiError | null;
  result: CloseResult | null;
}

const IDLE: CloseTableState = { loading: false, error: null, result: null };

export function useCloseTable() {
  const [state, setState] = useState<CloseTableState>(IDLE);

  const closeTable = useCallback(async (tableId: number): Promise<CloseResult> => {
    setState({ loading: true, error: null, result: null });
    try {
      const result = await apiClient.post<CloseResult>(`/api/admin/tables/${tableId}/close`);
      setState({ loading: false, error: null, result });
      return result;
    } catch (e) {
      const err = e instanceof ApiError ? e : new ApiError(0, { code: "NETWORK", message: String(e) });
      setState({ loading: false, error: err, result: null });
      throw err;
    }
  }, []);

  const reset = useCallback(() => setState(IDLE), []);

  return { ...state, closeTable, reset };
}
