/**
 * VersionCompare — task 5-9 "So sánh": diff between two versions of a step.
 *
 * BR-4 (a11y): additions/removals shown with a prefix (+/-) AND color, never
 * color alone. Renders one of two shapes depending on `CompareResponse.type`
 * (backend decides by step — outline/script => "text", storyboard/scene_set
 * => "scene_set"):
 *   - "text": side-by-side old/new columns built from the unified diff.
 *   - "scene_set": added/removed/changed scene list.
 *
 * AC-1: closing must return focus to wherever the user opened it from — this
 * component itself doesn't own focus-restore (the opener does, since it
 * knows what to refocus); it only guarantees `onClose` is always reachable
 * via a real, focusable close button.
 */

"use client";

import { useEffect, useState } from "react";
import { compareVersions, type CompareResponse } from "@/lib/api/versions";
import { parseUnifiedDiff, toSideBySide } from "@/lib/diff/textDiff";
import { buildSceneDiffList } from "@/lib/diff/sceneDiff";

export interface VersionCompareProps {
  projectId: string;
  step: string;
  fromVersion: number;
  toVersion: number;
  onClose: () => void;
}

export default function VersionCompare({
  projectId,
  step,
  fromVersion,
  toVersion,
  onClose,
}: VersionCompareProps) {
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    compareVersions(projectId, step, fromVersion, toVersion)
      .then((res) => {
        if (!cancelled) setResult(res);
      })
      .catch(() => {
        if (!cancelled) setError("Không so sánh được hai phiên bản này");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, step, fromVersion, toVersion]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label={`So sánh v${fromVersion} với v${toVersion}`}
    >
      <div className="flex max-h-[85vh] w-full max-w-4xl flex-col gap-4 rounded-xl border border-border bg-card p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            So sánh v{fromVersion} ↔ v{toVersion}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            Đóng
          </button>
        </div>

        <div className="overflow-y-auto">
          {loading && <p className="text-sm text-muted-foreground">Đang so sánh…</p>}
          {error && <p className="text-sm text-status-fail">{error}</p>}
          {!loading && !error && result?.type === "text" && <TextDiffView diff={result.diff ?? ""} />}
          {!loading && !error && result?.type === "scene_set" && (
            <SceneDiffView
              added={result.added ?? []}
              removed={result.removed ?? []}
              changed={result.changed ?? []}
            />
          )}
          {!loading && !error && result?.type === "raw" && (
            <div className="grid grid-cols-2 gap-4 text-xs">
              <pre className="whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-3">
                {JSON.stringify(result.v1_content, null, 2)}
              </pre>
              <pre className="whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-3">
                {JSON.stringify(result.v2_content, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TextDiffView({ diff }: { diff: string }) {
  const lines = parseUnifiedDiff(diff);
  const { left, right } = toSideBySide(lines);

  if (left.length === 0 && right.length === 0) {
    return <p className="text-sm text-muted-foreground">Không có khác biệt.</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-4 font-mono text-xs">
      <DiffColumn title={`v${1}`} lines={left} />
      <DiffColumn title="Hiện hành" lines={right} />
    </div>
  );
}

function DiffColumn({ title, lines }: { title: string; lines: { type: string; text: string }[] }) {
  return (
    <div className="rounded-lg border border-border bg-muted/40 p-3">
      <p className="mb-2 text-xs font-semibold text-muted-foreground">{title}</p>
      <div className="space-y-0.5">
        {lines.map((line, i) => (
          <div
            key={i}
            // BR-4 a11y: prefix character (+/-) always rendered alongside
            // color — never color alone.
            className={
              line.type === "add"
                ? "bg-status-pass/10 text-status-pass"
                : line.type === "remove"
                  ? "bg-status-fail/10 text-status-fail"
                  : "text-foreground"
            }
          >
            {line.text || " "}
          </div>
        ))}
      </div>
    </div>
  );
}

function SceneDiffView({
  added,
  removed,
  changed,
}: {
  added: string[];
  removed: string[];
  changed: { scene_id: string; fields: string[] }[];
}) {
  const entries = buildSceneDiffList(added, removed, changed);

  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">Không có khác biệt.</p>;
  }

  return (
    <ul className="space-y-1 text-sm">
      {entries.map((e) => (
        <li
          key={`${e.kind}-${e.sceneId}`}
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 ${
            e.kind === "added"
              ? "border-status-pass/30 bg-status-pass/10 text-status-pass"
              : e.kind === "removed"
                ? "border-status-fail/30 bg-status-fail/10 text-status-fail"
                : "border-status-warn/30 bg-status-warn/10 text-status-warn"
          }`}
        >
          {/* BR-4 a11y: prefix character always rendered, not color-only. */}
          <span aria-hidden="true" className="font-mono font-bold">
            {e.prefix}
          </span>
          <span className="font-medium">{e.sceneId}</span>
          {e.kind === "changed" && e.fields && e.fields.length > 0 && (
            <span className="text-xs text-muted-foreground">({e.fields.join(", ")})</span>
          )}
        </li>
      ))}
    </ul>
  );
}
