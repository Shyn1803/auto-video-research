/**
 * useAutosave — 1s debounce autosave with offline resilience (BR-3).
 *
 * Behavior:
 *  - edits → status "saving" → debounce 1s → API PUT → "saved" or "error"
 *  - offline → status: "offline", cached. On reconnect → retry with exponential
 *    back-off (max 5 attempts). Content never lost.
 *  - 422 response → map field_path → inline errors; surface via onFieldError
 *
 * AC-1:  edit → Player reflects <100 ms (form is local-first; PUT debounced)
 * BR-3:  offline → "⚠ chưa lưu" badge, reconnect → auto-save
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseAutosaveOptions<T> {
  /** PUT autosave target */
  save: (value: T) => Promise<void>;
  /** local debounce ms (1s per BR-3) */
  debounceMs?: number;
  /** called when the component first mounts — initial value */
  initialValue: T;
  /** 422 errors mapped by field_path */
  onFieldError?: (errors: Record<string, string>) => void;
}

interface UseAutosaveReturn<T> {
  value: T;
  setValue: (next: T | ((prev: T) => T)) => void;
  status: "saved" | "saving" | "error" | "offline";
  retryCount: number;
  manuallySave: () => Promise<void>;
}

export function useAutosave<T>({
  save,
  debounceMs = 1000,
  initialValue,
  onFieldError,
}: UseAutosaveOptions<T>): UseAutosaveReturn<T> {
  const [value, _setValue] = useState<T>(initialValue);
  const [status, _setStatus] =
    useState<UseAutosaveReturn<T>["status"]>("saved");
  const [retryCount, _setRetryCount] = useState(0);
  const dirtyRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const retryRef = useRef(0);
  const latestValueRef = useRef<T>(value);
  const onlineRef = useRef(navigator.onLine);

  latestValueRef.current = value;
  onlineRef.current = navigator.onLine;

  const setValue = useCallback((next: T | ((v: T) => T)) => {
    _setValue((prev) => {
      const resolved = typeof next === "function" ? (next as (v: T) => T)(prev) : next;
      dirtyRef.current = true;
      _setStatus((s) => (onlineRef.current && s !== "error" ? "saving" : "offline"));
      return resolved;
    });
  }, []);

  const attemptSave = useCallback(
    async (v: T): Promise<boolean> => {
      try {
        await save(v);
        dirtyRef.current = false;
        retryRef.current = 0;
        _setRetryCount(0);
        _setStatus("saved");
        return true;
      } catch (err: unknown) {
        const axiosErr = err as {
          response?: { status: number; data?: { detail?: Record<string, string> } };
        };
        if (axiosErr.response?.status === 422) {
          // Map field_path errors
          const detail = axiosErr.response.data?.detail;
          if (detail && typeof detail === "object") {
            onFieldError?.(detail as Record<string, string>);
          }
          _setStatus("error");
          return false;
        }
        // Network or other — treat as recoverable when online
        if (onlineRef.current && retryRef.current < 5) {
          retryRef.current += 1;
          _setRetryCount(retryRef.current);
          _setStatus("saving");
          return false;
        }
        _setStatus(navigator.onLine ? "error" : "offline");
        return false;
      }
    },
    [save, onFieldError],
  );

  // Flush loop — retries until success or 5 attempts exhausted
  const flush = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!dirtyRef.current) return;

    const attempt = async () => {
      const ok = await attemptSave(latestValueRef.current);
      if (!ok && navigator.onLine && retryRef.current < 5) {
        timerRef.current = setTimeout(attempt, 1000 * Math.pow(2, retryRef.current));
      }
    };
    attempt();
  }, [attemptSave]);

  // Debounced save
  useEffect(() => {
    if (!dirtyRef.current) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (navigator.onLine) {
        flush();
      } else {
        _setStatus("offline");
      }
    }, debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, debounceMs, flush]);

  // Online handler
  useEffect(() => {
    const on = () => {
      _setStatus((prev) => (prev === "offline" ? "saving" : prev));
      if (dirtyRef.current) flush();
    };
    const off = () => {
      if (dirtyRef.current) _setStatus("offline");
    };
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, [flush]);

  const manuallySave = useCallback(async () => {
    _setStatus("saving");
    await attemptSave(value);
  }, [value, attemptSave]);

  return { value, setValue, status, retryCount, manuallySave };
}
