/**
 * StatusBadge — design-system §3.1
 *
 * `kind`: pass|warn|fail|run|idle  (no arbitrary colors — maps to fixed tokens)
 * Icon auto: ✓ ⚠ ✗ ● ○
 * A11y: role="status", readable label
 */

"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  Circle,
} from "lucide-react";

const statusMap = {
  pass: { icon: CheckCircle2, label: "Đạt", dot: "bg-status-pass" },
  warn: { icon: AlertTriangle, label: "Cần xem", dot: "bg-status-warn" },
  fail: { icon: XCircle,     label: "Lỗi",   dot: "bg-status-fail" },
  run:  { icon: Loader2,     label: "Đang chạy", dot: "bg-status-run" },
  idle: { icon: Circle,      label: "Chưa", dot: "bg-status-idle" },
} as const;

type BadgeKind = keyof typeof statusMap;

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold leading-none",
  {
    variants: {
      kind: {
        pass: "bg-status-pass/10 text-status-pass border border-status-pass/30",
        warn: "bg-status-warn/10 text-status-warn border border-status-warn/30",
        fail: "bg-status-fail/10 text-status-fail border border-status-fail/30",
        run:  "bg-status-run/10 text-status-run border border-status-run/30",
        idle: "bg-status-idle/10 text-status-idle border border-status-idle/30",
      },
      pulse: {
        true: "animate-pulse",
        false: "",
      },
    },
    defaultVariants: {
      kind: "idle",
      pulse: false,
    },
  }
);

interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  kind: BadgeKind;
  label?: string;
  pulse?: boolean;
}

export function StatusBadge({
  kind,
  label,
  pulse,
  className,
  ...rest
}: StatusBadgeProps) {
  const cfg = statusMap[kind];
  const Icon = cfg.icon;
  const displayLabel = label ?? cfg.label;

  return (
    <span
      role="status"
      aria-label={`Trạng thái: ${displayLabel}`}
      className={cn(badgeVariants({ kind, pulse }), className)}
      {...rest}
    >
      <Icon
        className={cn(
          "size-3.5 shrink-0",
          kind === "run" && "animate-spin",
          kind === "warn" && pulse && "animate-pulse"
        )}
        aria-hidden="true"
      />
      {displayLabel}
    </span>
  );
}
