"use client";

import { useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, setAccessToken } from "@/lib/api/interceptor";

type FormState = "default" | "loading" | "error";

interface LoginError {
  message: string;
  retryAfter?: number;
}

export default function LoginPage() {
  const [state, setState] = useState<FormState>("default");
  const [error, setError] = useState<LoginError | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [countdown, setCountdown] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startCountdown = (seconds: number) => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setCountdown(seconds);
    intervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (state === "loading") return;

    setError(null);
    setCountdown(0);

    try {
      setState("loading");
      const res = await api.post<{ access_token: string }>("/auth/login", {
        email,
        password,
      });

      setAccessToken(res.data.access_token);
      window.location.href = "/";
    } catch (err: unknown) {
      setState("error");
      const axiosErr = err as {
        response?: {
          status: number;
          data: { detail?: string } | Record<string, unknown>;
          headers: Record<string, string | undefined>;
        };
      };

      if (axiosErr.response?.status === 429) {
        const data = axiosErr.response.data as { detail?: string };
        const retryAfter = Number(
          axiosErr.response.headers["retry-after"] ?? 900,
        );
        startCountdown(retryAfter);
        setError({
          message: (data?.detail as string) ?? "Quá nhiều lần thử. Vui lòng đợi.",
          retryAfter,
        });
      } else {
        const data = axiosErr.response?.data as { detail?: string } | undefined;
        setError({
          message: (data?.detail as string) ??
            "Email hoặc mật khẩu không chính xác.",
        });
      }
    } finally {
      setState((s) => (s === "loading" ? "default" : "error"));
    }
  };

  const isLocked = countdown > 0;
  const disabled =
    state === "loading" || (!email || !password) || isLocked;

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-6 text-slate-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-5 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl"
      >
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-cyan-300">
            AVR
          </p>
          <h1 className="mt-2 text-2xl font-semibold">Đăng nhập</h1>
          <p className="mt-1 text-sm text-slate-400">
            Nền tảng nghiên cứu tự động video
          </p>
        </div>

        <label className="block space-y-1 text-sm" htmlFor="email">
          <span className="text-slate-300">Email</span>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50 outline-none focus:border-cyan-300 disabled:opacity-60"
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="creator@example.com"
            disabled={isLocked}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label className="block space-y-1 text-sm" htmlFor="password">
          <span className="text-slate-300">Mật khẩu</span>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50 outline-none focus:border-cyan-300 disabled:opacity-60"
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••••"
            disabled={isLocked}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        {error && (
          <p
            className="text-sm text-red-400"
            role="alert"
            aria-live="assertive"
          >
            {error.message}
            {isLocked && (
              <span className="ml-2 font-mono">
                {" "}
                Còn {Math.floor(countdown / 60)}:{(countdown % 60).toString().padStart(2, "0")}
              </span>
            )}
          </p>
        )}

        <button
          className="w-full rounded-md bg-cyan-400 px-3 py-2 font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled}
          type="submit"
        >
          {state === "loading"
            ? "Đang xác thực…"
            : isLocked
              ? "Đang khóa…"
              : "Đăng nhập"}
        </button>

        <p className="text-center text-xs text-slate-500">
          Chưa có tài khoản?{" "}
          <Link
            href="#"
            className="text-cyan-300 underline hover:no-underline"
          >
            Liên hệ quản trị viên
          </Link>
        </p>
      </form>
    </main>
  );
}
