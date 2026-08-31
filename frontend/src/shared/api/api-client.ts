// ApiClient (U1) — REST wrapper: injects auth header, parses structured error body -> ApiError.
// Owned by U1; each unit adds its own endpoint calls on top. See component-methods.md §4.4.

export const AUTH_TOKEN_KEY = "auth_token";

export interface ApiErrorShape {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export class ApiError extends Error {
  code: string;
  details?: Record<string, unknown> | null;
  status: number;

  constructor(status: number, body: ApiErrorShape) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? null;
  }
}

export interface RequestOptions {
  headers?: Record<string, string>;
  auth?: boolean; // attach Authorization header (default true)
  signal?: AbortSignal;
}

function authHeaders(opts?: RequestOptions): Record<string, string> {
  if (opts?.auth === false) return {};
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(method: string, path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(opts),
      ...(opts?.headers ?? {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: opts?.signal,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!res.ok) {
    const err = (data?.error ?? { code: "INTERNAL", message: res.statusText }) as ApiErrorShape;
    throw new ApiError(res.status, err);
  }
  return data as T;
}

export const apiClient = {
  get: <T>(path: string, opts?: RequestOptions) => request<T>("GET", path, undefined, opts),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>("POST", path, body, opts),
  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>("PATCH", path, body, opts),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>("PUT", path, body, opts),
  delete: <T>(path: string, opts?: RequestOptions) => request<T>("DELETE", path, undefined, opts),
};
