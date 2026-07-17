/**
 * Topbar — Workspace shell header (Step 1).
 *
 * Per wireframe + design-system §4.1 pattern:
 *   ← Dự án | Tên project + ⓘ + StatusBadge | [VersionSwitcher slot] | ▶ Xem bản mới nhất
 *
 * BR-7: ▸ Xem bản mới nhất always visible; project name ⓘ opens ProjectDrawer
 */

"use client";

import { useRouter } from "next/navigation";
import { useWorkspace, STATIONS } from "@/lib/workspace-context";
import { StatusBadge } from "@/components/ui/status-badge";

function projectStatusKind(status: string) {
  switch (status) {
    case "publish_ready": return "pass";
    case "review":        return "warn";
    case "running":       return "run";
    case "error":         return "fail";
    default:              return "idle";
  }
}

function projectStatusLabel(status: string) {
  switch (status) {
    case "publish_ready": return "Sẵn sàng";
    case "review":        return "Cần duyệt";
    case "running":       return "Đang chạy";
    case "error":         return "Lỗi";
    default:              return "Chờ";
  }
}

export default function Topbar() {
  const { state, dispatch } = useWorkspace();
  const router = useRouter();

  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-border pb-3">
      {/* ← Back to dashboard */}
      <button
        type="button"
        onClick={() => router.back()}
        className="rounded-lg px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        ← Dự án
      </button>

      {/* Project name + info (opens drawer — 5-10) */}
      <button
        type="button"
        onClick={() => dispatch({ type: "OPEN_DRAWER" })}
        className="inline-flex items-center gap-1 text-lg font-semibold transition-colors hover:text-primary"
        title="Thông tin & cài đặt dự án"
      >
        {state.projectName || "Dự án"}
        <InfoIcon />
      </button>

      {/* StatusBadge — project-level (BR-7) */}
      <StatusBadge
        kind={projectStatusKind(state.projectStatus)}
        label={projectStatusLabel(state.projectStatus)}
      />

      {/* VersionSwitcher slot — 5-9 populates; null placeholder for now */}
      <span className="ml-auto flex items-center gap-3">
        <VersionSwitcherCurrent />
        {/* ▶ Xem bản mới nhất — BR-7 */}
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          ▶ Xem bản mới nhất
        </button>
      </span>
    </header>
  );
}

function InfoIcon() {
  return (
    <span
      aria-label="Thông tin dự án"
      className="inline-flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded-full bg-muted text-[10px]"
    >
      ⓘ
    </span>
  );
}

function VersionSwitcherCurrent() {
  return (
    <details className="relative">
      <summary className="list-none cursor-pointer">
        <span className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent">
          Phiên bản v1 ▾
        </span>
      </summary>

      {/* Minimal stub; 5-9 fills with full version history + actions. */}
      <div
        role="dialog"
        className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-border bg-card p-4 shadow-xl"
      >
        {STATIONS.map((s) => (
          <div
            key={s.key}
            className="flex items-center justify-between border-b border-border px-1 py-1.5 last:border-0"
          >
            <span className="text-sm">{s.label}</span>
            <span className="text-xs text-muted-foreground">v1 · AI ·</span>
          </div>
        ))}
        <p className="mt-2 px-1 text-xs text-muted-foreground/70">
          5-9: VersionSwitcher nội dung
        </p>
      </div>
    </details>
  );
}
