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
import { useWorkspace } from "@/lib/workspace-context";
import { StatusBadge } from "@/components/ui/status-badge";
import VersionSwitcher from "./VersionSwitcher";

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

      {/* VersionSwitcher — task 5-9 */}
      <span className="ml-auto flex items-center gap-3">
        <VersionSwitcher />
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
