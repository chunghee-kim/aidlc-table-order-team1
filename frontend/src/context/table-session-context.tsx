// TableSessionContext (implemented by U2/A). component-methods.md §4.2
// Tablet auto-login: the admin's table setup persists {storeCode, tableNumber, tablePassword} to
// localStorage (TABLE_CONFIG_KEY). bootstrap() resolves store/table identity via /table-login and
// keeps it across refreshes. Session lifecycle (session_id) is started lazily on first order (U6).
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { apiClient } from "../shared/api/api-client";

export const TABLE_CONFIG_KEY = "table_config";

export interface TableConfig {
  storeCode: string;
  tableNumber: number;
  tablePassword: string;
}

export interface TableSessionInfo {
  storeId: number;
  tableId: number;
  sessionId: number | null;
}

export interface TableSessionContextValue {
  bootstrap(): Promise<void>; // localStorage setup -> resolve_session_context; survives refresh
  getContext(): TableSessionInfo | null;
  isConfigured(): boolean; // prompt initial setup when false
}

interface TableLoginResponse {
  store_id: number;
  table_id: number;
}

/** Read the persisted tablet config, if any. */
export function readTableConfig(): TableConfig | null {
  const raw = localStorage.getItem(TABLE_CONFIG_KEY);
  if (!raw) return null;
  try {
    const cfg = JSON.parse(raw) as Partial<TableConfig>;
    if (typeof cfg.storeCode === "string" && typeof cfg.tableNumber === "number" &&
        typeof cfg.tablePassword === "string") {
      return { storeCode: cfg.storeCode, tableNumber: cfg.tableNumber, tablePassword: cfg.tablePassword };
    }
  } catch {
    /* fall through */
  }
  return null;
}

/** Persist the tablet config (called by the admin TableSetupView / manual table login). */
export function saveTableConfig(cfg: TableConfig): void {
  localStorage.setItem(TABLE_CONFIG_KEY, JSON.stringify(cfg));
}

export function clearTableConfig(): void {
  localStorage.removeItem(TABLE_CONFIG_KEY);
}

const TableSessionContext = createContext<TableSessionContextValue | null>(null);

export function TableSessionProvider({ children }: { children: ReactNode }) {
  const [info, setInfo] = useState<TableSessionInfo | null>(null);
  // Ref mirror so getContext() returns the latest value without stale closures.
  const infoRef = useRef<TableSessionInfo | null>(null);

  const bootstrap = useCallback(async () => {
    const cfg = readTableConfig();
    if (!cfg) {
      infoRef.current = null;
      setInfo(null);
      return;
    }
    const res = await apiClient.post<TableLoginResponse>(
      "/api/customer/table-login",
      { store_code: cfg.storeCode, table_number: cfg.tableNumber, table_password: cfg.tablePassword },
      { auth: false },
    );
    const next: TableSessionInfo = { storeId: res.store_id, tableId: res.table_id, sessionId: null };
    infoRef.current = next;
    setInfo(next);
  }, []);

  const getContext = useCallback(() => infoRef.current, []);
  const isConfigured = useCallback(() => readTableConfig() !== null, []);

  // `info` is referenced so provider consumers re-render after bootstrap resolves.
  void info;

  const value: TableSessionContextValue = { bootstrap, getContext, isConfigured };
  return <TableSessionContext.Provider value={value}>{children}</TableSessionContext.Provider>;
}

export function useTableSession(): TableSessionContextValue {
  const ctx = useContext(TableSessionContext);
  if (!ctx) throw new Error("useTableSession must be used within TableSessionProvider");
  return ctx;
}
