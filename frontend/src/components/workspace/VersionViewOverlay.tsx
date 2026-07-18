/**
 * VersionViewOverlay — task 5-9 "Xem": readonly overlay of a past version's
 * full content, rendered without leaving the current screen/route.
 *
 * Fetches content via the additive `GET .../versions/{version}` endpoint
 * (VersionOut alone has no `content` — see lib/api/versions.ts). Purely
 * readonly: no editable fields, no save affordance — closing it never
 * mutates the underlying editable state (AC-1).
 */

"use client";

import { useEffect, useState } from "react";
import { getVersionDetail } from "@/lib/api/versions";

export interface VersionViewOverlayProps {
  projectId: string;
  step: string;
  version: number;
  onClose: () => void;
}

function formatContent(content: Record<string, unknown>): string {
  return JSON.stringify(content, null, 2);
}

export default function VersionViewOverlay({
  projectId,
  step,
  version,
  onClose,
}: VersionViewOverlayProps) {
  const [content, setContent] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getVersionDetail(projectId, step, version)
      .then((detail) => {
        if (!cancelled) setContent(detail.content);
      })
      .catch(() => {
        if (!cancelled) setError("Không tải được nội dung phiên bản này");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, step, version]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label={`Xem phiên bản v${version} (chỉ đọc)`}
    >
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col gap-4 rounded-xl border border-border bg-card p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            Xem v{version} <span className="text-xs font-normal text-muted-foreground">(chỉ đọc)</span>
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            Đóng
          </button>
        </div>

        <div className="overflow-y-auto rounded-lg border border-border bg-muted/40 p-3" aria-readonly="true">
          {loading && <p className="text-sm text-muted-foreground">Đang tải…</p>}
          {error && <p className="text-sm text-status-fail">{error}</p>}
          {!loading && !error && content && (
            <pre className="whitespace-pre-wrap break-words text-sm">{formatContent(content)}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
