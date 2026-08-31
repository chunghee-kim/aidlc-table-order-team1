// AuthContext (contract frozen in Phase 0; implemented by U2/A). component-methods.md §4.1
import { createContext, useContext, type ReactNode } from "react";
import { AUTH_TOKEN_KEY } from "../shared/api/api-client";

export interface AuthContextValue {
  login(storeCode: string, username: string, password: string): Promise<void>;
  logout(): void;
  getToken(): string | null;
  isAuthenticated(): boolean; // includes 16h expiry check (implemented in U2/A)
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Phase 0 stub. U2/A replaces login/isAuthenticated with real JWT handling.
const stubValue: AuthContextValue = {
  async login(_storeCode, _username, _password) {
    throw new Error("AuthContext.login not implemented (U2/A owns).");
  },
  logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  },
  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },
  isAuthenticated() {
    return localStorage.getItem(AUTH_TOKEN_KEY) !== null;
  },
};

export function AuthProvider({ children }: { children: ReactNode }) {
  return <AuthContext.Provider value={stubValue}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
