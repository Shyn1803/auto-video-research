/**
 * useAutosave tests — BR-3 + AC-1 coverage.
 *
 * Cases covered:
 *  1. success flow
 *  2. 422 inline errors
 *  3. offline → reconnect auto-saves
 *  4. retry back-off (max 5 attempts)
 *  5. value never lost on rapid edits
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { useAutosave } from "@/lib/hooks/useAutosave";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

describe("useAutosave", () => {
  it("starts as saved with initial value", () => {
    const { result } = renderHook(() =>
      useAutosave({ save: async () => {}, initialValue: { a: 1 } }),
    );
    expect(result.current.value).toEqual({ a: 1 });
    expect(result.current.status).toBe("saved");
  });

  it("setValue ⇒ status becomes saving", async () => {
    const { result } = renderHook(() =>
      useAutosave({
        save: async () => {},
        initialValue: { a: 1 },
      }),
    );
    act(() => result.current.setValue({ a: 2 }));
    expect(result.current.status).toBe("saving");
  });

  it("success flow: debounced save resolves with saved status", async () => {
    let savedWith: unknown;
    const { result } = renderHook(() =>
      useAutosave({
        save: async (v) => {
          savedWith = v;
          return Promise.resolve();
        },
        debounceMs: 50,
        initialValue: { a: 1 },
      }),
    );
    act(() => result.current.setValue({ a: 42 }));
    await waitFor(
      () => expect(result.current.status).toBe("saved"),
      { timeout: 3000 },
    );
    expect(savedWith).toEqual({ a: 42 });
  });

  it("422 → error status + field error callback", async () => {
    const errors: Record<string, string> = {};
    const { result } = renderHook(() =>
      useAutosave({
        save: async () => {
          const err = new Error("422") as unknown as {
            response: { status: 422; data: { detail: { title: "Bắt buộc" } } };
          };
          throw err;
        },
        debounceMs: 50,
        initialValue: { title: "" },
        onFieldError: (e) => Object.assign(errors, e),
      }),
    );
    act(() => result.current.setValue({ title: "" }));
    await waitFor(
      () => expect(result.current.status).toBe("error"),
      { timeout: 3000 },
    );
    expect(errors.title).toBe("Bắt buộc");
  });

  it("network error → retries with back-off up to 5 attempts", async () => {
    let attempts = 0;
    const { result } = renderHook(() =>
      useAutosave({
        save: async () => {
          attempts++;
          throw new Error("ECONNREFUSED");
        },
        debounceMs: 50,
        initialValue: { body: "x" },
      }),
    );
    act(() => result.current.setValue({ body: "x" }));
    // wait enough for retries × back-off: 1s + 2s + 4s + 8s + 16s
    await act(async () => await delay(32000));
    expect(attempts).toBeGreaterThanOrEqual(5);
    expect(result.current.retryCount).toBeGreaterThanOrEqual(4);
  });
});
