/**
 * Axios instance with auto-refresh interceptor.
 *
 * - Stores access token in memory (never persisted to localStorage/sessionStorage).
 * - On 401: calls /auth/refresh (browser sends httpOnly refresh cookie automatically),
 *   then retries the original request with the new access token.
 * - Concurrent 401s share a single refresh promise to avoid racing.
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig, type AxiosInstance, type AxiosResponse } from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/api`,
  withCredentials: true,
});

/* ── In-memory token ──────────────────────────────────── */

let accessToken: string | null = null;
let refreshPromise: Promise<string> | null = null;

/** Subscribe to token changes (used by AuthProvider to propagate state). */
export const tokenSubscribers = new Set<(token: string | null) => void>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  tokenSubscribers.forEach((fn) => fn(token));
}

export async function refreshTokens(): Promise<string> {
  /* If a refresh is already in-flight, share its result. */
  if (refreshPromise) return refreshPromise;

  refreshPromise = api
    .post<{ access_token: string }>("/auth/refresh", {})
    .then((res: AxiosResponse<{ access_token: string }>) => {
      const { access_token } = res.data;
      setAccessToken(access_token);
      return access_token;
    })
    .catch((err: AxiosError) => {
      setAccessToken(null);
      throw err;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

/* ── Request interceptor ─────────────────────────────── */

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

/* ── Response interceptor ────────────────────────────── */

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    /* ── 429 (rate-limit) — expose retry_after for countdown ── */
    if (error.response?.status === 429) {
      const retryAfter = Number(error.response.headers["retry-after"] ?? 0);
      return Promise.reject({ ...error, retryAfter });
    }

    /* ── 401 — attempt refresh once, then retry ── */
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        await refreshTokens();
        if (accessToken) {
          original.headers.Authorization = `Bearer ${accessToken}`;
          return api.request(original);
        }
      } catch {
        setAccessToken(null);
      }
    }

    return Promise.reject(error);
  },
);

export { API_BASE };
