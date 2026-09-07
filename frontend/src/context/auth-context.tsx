// AuthContext (implemented by U2/A). component-methods.md §4.1
// Admin JWT: login stores the token in localStorage; isAuthenticated() checks the 16h expiry
// by decoding the token payload (US-A-01/02).
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { apiClient, AUTH_TOKEN_KEY } from "../shared/api/api-client";

export interface AuthContextValue {
  login(storeCode: string, username: string, password: string): Promise<void>;
  logout(): void;
  getToken(): string | null;
  isAuthenticated(): boolean; // includes 16h expiry check
}

interface LoginResponse {
  token: string;
  admin: { id: number; username: string; store_id: number };
}

/** Decode the `exp` (seconds since epoch) from a JWT payload without verifying the signature. */
function tokenExpiryMs(token: string): number | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(base64)) as { exp?: number };
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

function isTokenValid(token: string | null): boolean {
  if (!token) return false;
  const expMs = tokenExpiryMs(token);
  // No exp claim -> treat as invalid (defensive); otherwise must be in the future.
  return expMs !== null && expMs > Date.now();
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(AUTH_TOKEN_KEY));

  const login = useCallback(async (storeCode: string, username: string, password: string) => {
    const res = await apiClient.post<LoginResponse>(
      "/api/admin/login",
      { store_code: storeCode, username, password },
      { auth: false },
    );
    localStorage.setItem(AUTH_TOKEN_KEY, res.token);
    setToken(res.token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setToken(null);
  }, []);

  const getToken = useCallback(() => localStorage.getItem(AUTH_TOKEN_KEY), []);

  const isAuthenticated = useCallback(() => isTokenValid(localStorage.getItem(AUTH_TOKEN_KEY)), [
    // token in deps so consumers re-render on login/logout
    token,
  ]);

  const value: AuthContextValue = { login, logout, getToken, isAuthenticated };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
