/**
 * Low-level SSE transport layer.
 *
 * Opens an EventSource, parses each ``data:`` line as JSON, and hands the parsed
 * object to ``onMessage``.  A heartbeat comment (sent by the server every 15 s)
 * keeps reverse-proxy idle timeouts from killing the connection.
 *
 * This module is intentionally transport-only — token lifecycle, reconnect
 * backoff, and resync logic all live in ``useEventStream.ts``.
 */

export type SseMessageHandler = (data: Record<string, unknown>) => void;

export interface SseOptions {
  /** Called once per SSE event (already parsed JSON). */
  onMessage(data: Record<string, unknown>): void;
  onError?(ev: Event): void;
  /** Called once when the browser fires the native ``close`` event. */
  onClose?(): void;
}

/**
 * Open an SSE connection. Returns a teardown function that closes the
 * EventSource — the caller is responsible for invoking it on unmount or
 * before opening a replacement connection.
 */
export function openSse(url: string, opts: SseOptions): () => void {
  const es = new EventSource(url);

  es.addEventListener("message", () => {
    // "message" is the default SSE event type — every bare ``data:`` line
    // dispatches here when no explicit ``event:`` name is set by the server.
    try {
      const raw = (es as EventSource & { data?: string }).data ?? "{}";
      const data = JSON.parse(raw) as Record<string, unknown>;
      opts.onMessage(data);
    } catch {
      // malformed JSON — skip silently, don't break the stream
    }
  });

  es.onerror = (ev: Event) => {
    opts.onError?.(ev);
    // Browser automatically transitions the connection to CLOSED on error;
    // we keep the instance alive so the caller can inspect readyState.
  };

  return () => {
    if (es.readyState !== EventSource.CLOSED) {
      es.close();
    }
    opts.onClose?.();
  };
}
