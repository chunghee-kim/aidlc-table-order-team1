// TableSessionContext (contract frozen in Phase 0; implemented by U2/A). component-methods.md §4.2
import { createContext, useContext, type ReactNode } from "react";

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

const TableSessionContext = createContext<TableSessionContextValue | null>(null);

// Phase 0 stub. U2/A replaces with real localStorage + resolve_session_context wiring.
const stubValue: TableSessionContextValue = {
  async bootstrap() {
    throw new Error("TableSessionContext.bootstrap not implemented (U2/A owns).");
  },
  getContext() {
    return null;
  },
  isConfigured() {
    return false;
  },
};

export function TableSessionProvider({ children }: { children: ReactNode }) {
  return <TableSessionContext.Provider value={stubValue}>{children}</TableSessionContext.Provider>;
}

export function useTableSession(): TableSessionContextValue {
  const ctx = useContext(TableSessionContext);
  if (!ctx) throw new Error("useTableSession must be used within TableSessionProvider");
  return ctx;
}
