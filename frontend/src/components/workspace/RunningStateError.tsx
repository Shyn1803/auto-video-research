/**
 * RunningStateError — classified error state for a failed AI step (BR-2).
 *
 * Two shapes, matching `app/core/exceptions.py::AllProvidersFailed` on the
 * backend (the run's `error` field, surfaced via `GET
 * /projects/{id}/runs/{run_id}` per `docs/specs/api-spec.md` — no event
 * dedicated to errors exists in `docs/specs/event-catalog.md` yet, so this
 * component takes a pre-classified `error` prop rather than parsing SSE
 * itself; whichever page wires this in (Step 5 / 5-6 / 5-7) is responsible
 * for shaping the run's `error` string/JSON into one of these two variants):
 *
 * - `all_providers_failed` — every provider in the chain for one capability
 *   was exhausted/rejected. Renders the provider+reason list. BR-2: an
 *   admin viewer gets a "Quản trị › Providers" link (there is no dedicated
 *   admin/providers page yet, so this links to the closest existing one,
 *   `/admin/api-keys` — flagged in state file decisions); a creator viewer
 *   gets "báo quản trị viên" instead, never the raw provider list framed as
 *   actionable for them.
 * - `generic` — anything else: a translated/human message up front, with
 *   the raw technical detail behind a collapsible `<details>` (native,
 *   a11y-friendly disclosure — no extra JS state needed for AC-5).
 *
 * `viewerRole` is caller-supplied rather than read from a shared auth hook:
 * `AuthProvider`/`useAuth` (task 1-x) doesn't carry a `role` field today, so
 * inventing one here would be a scope-creeping auth change, not a
 * RunningState concern. The Step 5 integration point is expected to supply
 * whatever role source exists at that point in the app.
 */

"use client";

export interface ProviderFailure {
  provider: string;
  reason: string;
  retryable?: boolean;
}

export interface AllProvidersFailedError {
  kind: "all_providers_failed";
  capability: string;
  chain: string[];
  failures: ProviderFailure[];
}

export interface GenericRunError {
  kind: "generic";
  /** Human/translated message — never the raw exception string up front. */
  message: string;
  /** Raw technical detail, shown only inside the collapsible section. */
  technicalDetail?: string;
}

export type RunningStateErrorData = AllProvidersFailedError | GenericRunError;

export type ViewerRole = "admin" | "creator";

export interface RunningStateErrorProps {
  error: RunningStateErrorData;
  viewerRole: ViewerRole;
  onRetry?: () => void;
  className?: string;
}

const CAPABILITY_LABEL: Record<string, string> = {
  llm_cheap: "AI (tầng rẻ)",
  llm_strong: "AI (tầng mạnh)",
  tts: "Giọng đọc",
  search: "Tìm kiếm",
  image_gen: "Tạo ảnh",
};

export default function RunningStateError({
  error,
  viewerRole,
  onRetry,
  className,
}: RunningStateErrorProps) {
  const isChainExhausted = error.kind === "all_providers_failed";

  return (
    <div
      role="alert"
      data-error-kind={error.kind}
      className={`flex flex-col gap-3 rounded-xl border border-status-fail/40 bg-status-fail/5 p-6 ${className ?? ""}`}
    >
      {isChainExhausted ? (
        <>
          <h3 className="text-sm font-semibold text-status-fail">
            Không thể tiếp tục — hết nhà cung cấp cho{" "}
            {CAPABILITY_LABEL[error.capability] ?? error.capability}
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
            {error.failures.map((f, i) => (
              <li key={`${f.provider}-${i}`}>
                <span className="font-medium">{f.provider}</span> — {f.reason}
              </li>
            ))}
          </ul>
          {viewerRole === "admin" ? (
            <a
              href="/admin/api-keys"
              className="text-sm font-medium text-primary underline underline-offset-2"
            >
              Quản trị › Providers
            </a>
          ) : (
            <p className="text-sm text-muted-foreground">
              Vui lòng báo quản trị viên để bổ sung nhà cung cấp.
            </p>
          )}
        </>
      ) : (
        <>
          <h3 className="text-sm font-semibold text-status-fail">{error.message}</h3>
          {error.technicalDetail && (
            <details className="text-xs text-muted-foreground">
              <summary className="cursor-pointer select-none">Chi tiết kỹ thuật</summary>
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words rounded bg-muted p-2">
                {error.technicalDetail}
              </pre>
            </details>
          )}
        </>
      )}

      {onRetry && (
        <div className="pt-1">
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-primary px-4 py-1.5 text-sm font-semibold text-primary-foreground hover:brightness-110"
          >
            Thử lại
          </button>
        </div>
      )}
    </div>
  );
}
