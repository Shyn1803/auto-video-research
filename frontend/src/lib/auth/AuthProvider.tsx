"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getAccessToken, refreshTokens, setAccessToken, tokenSubscribers } from "@/lib/api/interceptor";

/* ── Shape ────────────────────────────────────────────── */

interface AuthContextValue {
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refresh: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

/* ── Provider ─────────────────────────────────────────── */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getAccessToken);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handler = (t: string | null) => setToken(t);

    tokenSubscribers.add(handler);
    handler(getAccessToken());

    return () => {
      tokenSubscribers.delete(handler);
    };
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await refreshTokens();
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setAccessToken(null);
    setToken(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken: token,
      isAuthenticated: Boolean(token),
      isLoading: loading,
      refresh,
      logout,
    }),
    [token, loading, refresh, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
