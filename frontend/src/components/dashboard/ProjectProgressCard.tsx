/**
 * ProjectProgressCard — dashboard-level live progress card for a backgrounded run.
 *
 * Task 5-8 Step 2 (AC-2): when a Content Creator clicks "Chạy ngầm" on
 * RunningState, the project dashboard (`/projects`, see
 * `src/app/projects/page.tsx`) should show this instead of/alongside the
 * regular `ProjectCard` for that project — a live `●%`/indeterminate
 * readout that, on click, returns the user to the workspace at its current
 * station (the existing `/projects/{id}` → `/projects/{id}/scenes` redirect
 * plus WorkspaceProvider's server-loaded station state already restores
 * "exact screen, exact progress" — this card only needs to navigate there;
 * it does not re-derive that restoration logic, which belongs to 5-1/5-6).
 *
 * Reuses `useEventStream` (task 1-6) rather than opening a second SSE
 * connection type — same BR-1 real-message/no-fabricated-% contract as
 * RunningState. The `useEventStreamHook` prop is a test seam so unit tests
 * don't need a real EventSource/backend.
 */

"use client";

import { useRouter } from "next/navigation";
import { useEventStream, type UseEventStreamOptions, type RunProgress } from "@/hooks/useEventStream";

export interface ProjectProgressCardProps {
  projectId: string;
  projectName: string;
  runId: string;
  /** Optional static label (e.g. "Nghiên cứu") shown until an SSE event arrives. */
  stepLabel?: string;
  onOpen?: (projectId: string) => void;
  /** Test seam — inject a fake stream hook instead of opening a real SSE connection. */
  useEventStreamHook?: (opts: UseEventStreamOptions) => RunProgress;
}

const STEP_LABEL: Record<string, string> = {
  research: "Nghiên cứu",
  content: "Nội dung",
  scenes: "Phân cảnh",
  finish: "Hoàn thiện",
  publish: "Xuất bản",
};

export function ProjectProgressCard({
  projectId,
  projectName,
  runId,
  stepLabel,
  onOpen,
  useEventStreamHook = useEventStream,
}: ProjectProgressCardProps) {
  const router = useRouter();
  const { progressPct, currentStep, lastEvent } = useEventStreamHook({ projectId, runId });

  // Same BR-1 rule as RunningState: only a genuine in-between fraction is
  // "determinate" -- today's backend's 0/100 sentinel values render as ●.
  const isDeterminate = progressPct > 0 && progressPct < 100;
  const message =
    (lastEvent?.payload as { message?: string } | undefined)?.message ?? null;
  const label = STEP_LABEL[currentStep ?? ""] ?? stepLabel ?? "Đang chạy";

  const handleOpen = () => {
    if (onOpen) onOpen(projectId);
    else router.push(`/projects/${projectId}`);
  };

  return (
    <div
      role="link"
      tabIndex={0}
      aria-label={`Quay lại dự án đang chạy ngầm ${projectName}`}
      onClick={handleOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter") handleOpen();
      }}
      className="flex cursor-pointer items-center gap-3 rounded-lg border border-primary/40 bg-primary/5 p-3 outline-none hover:border-primary focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span
        aria-hidden="true"
        className={`text-lg text-primary ${isDeterminate ? "" : "motion-safe:animate-pulse"}`}
      >
        ●
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <b className="truncate">{projectName}</b>
        <span className="text-xs text-muted-foreground" data-testid="progress-caption">
          {label}
          {isDeterminate ? ` · ${progressPct}%` : " · đang xử lý"}
          {message ? ` — ${message}` : ""}
        </span>
      </div>
    </div>
  );
}
