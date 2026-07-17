"use client";

import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";

export interface ProjectListItem {
  id: string;
  name: string;
  topic: string;
  mode: string;
  status: string;
  formats: string[];
  step_count: number;
  next_action: { label: string; href: string };
  updated_at: string;
}

/** BR-6: badge kind + step-name derived from status — no mini-stepper on the card. */
const STATUS_BADGE: Record<string, "pass" | "warn" | "fail" | "run" | "idle"> = {
  NEED_REVIEW: "warn",
  RESEARCHING: "run",
  PRODUCING: "run",
  RENDERING: "run",
  PUBLISHING: "run",
  READY: "pass",
  PUBLISHED: "pass",
  FAILED: "fail",
  DRAFT: "idle",
  REVISING: "idle",
  APPROVED: "idle",
  ARCHIVED: "idle",
};

const STEP_ORDER = [
  "research",
  "outline",
  "script",
  "storyboard",
  "scene_set",
  "produce",
  "render",
  "publish",
];

const STEP_LABEL: Record<string, string> = {
  research: "Nghiên cứu",
  outline: "Dàn ý",
  script: "Kịch bản",
  storyboard: "Phân cảnh",
  scene_set: "Phân cảnh",
  produce: "Sản xuất",
  render: "Hoàn thiện",
  publish: "Xuất bản",
};

function stepProgressLabel(stepCount: number): string {
  const idx = Math.min(stepCount, STEP_ORDER.length - 1);
  const stepName = STEP_LABEL[STEP_ORDER[Math.max(idx, 0)]] ?? "Nghiên cứu";
  return `bước ${Math.max(stepCount, 1)}/5 · ${stepName}`;
}

export function ProjectCard({
  project,
  onArchive,
  onClone,
}: {
  project: ProjectListItem;
  onArchive?: (id: string) => void;
  onClone?: (id: string) => void;
}) {
  const router = useRouter();
  const badgeKind = STATUS_BADGE[project.status] ?? "idle";

  const open = () => router.push(project.next_action.href.startsWith("/") ? `/projects/${project.id}` : project.next_action.href);

  return (
    <div
      role="link"
      tabIndex={0}
      aria-label={`Mở dự án ${project.name}`}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === "Enter") open();
      }}
      className="card group flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 outline-none hover:border-primary focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div
        className="flex h-[92px] w-[52px] shrink-0 items-center justify-center rounded-md border border-dashed border-border bg-muted text-xs"
        aria-hidden="true"
      >
        {project.formats.includes("vertical_1080x1920") ? "▶" : "🖼"}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <b className="truncate">{project.name}</b>
          <StatusBadge kind={badgeKind} label={project.next_action.label} />
        </div>
        <div className="text-sm text-muted-foreground">
          {stepProgressLabel(project.step_count)}
        </div>
      </div>
      <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        {onClone && (
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onClone(project.id);
            }}
          >
            Nhân bản
          </Button>
        )}
        {onArchive && project.status !== "ARCHIVED" && (
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onArchive(project.id);
            }}
          >
            Lưu trữ
          </Button>
        )}
      </div>
    </div>
  );
}
