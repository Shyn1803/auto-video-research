/**
 * ApproveBar — design-system §3.3: sticky bottom-right of content area.
 *
 * States: enabled / disabled (tooltip mandatory) / loading.
 * Structure: [secondary ghost] [primary action].
 * Per decision: duyệt theo từng cảnh (not per-step).
 */

"use client";

import type { ReactNode } from "react";

interface ApproveBarProps {
  /** approximate of scenes approved (shown: "Đã duyệt 6/8") */
  approvedCount: number;
  totalScenes: number;
  onPrimaryAction: () => void;
  onSecondaryAction: () => void;
  primaryLabel?: string;
  secondaryLabel?: string;
  /** if set, bar is disabled and this explains why (required by design-system §3.3) */
  disabledReason?: string;
  loading?: boolean;
  children?: ReactNode;
}

export function ApproveBar({
  approvedCount,
  totalScenes,
  onPrimaryAction,
  onSecondaryAction,
  primaryLabel = "Sang Hoàn thiện ▸",
  secondaryLabel = "↻ Regen",
  disabledReason,
  loading = false,
  children,
}: ApproveBarProps) {
  const allApproved = approvedCount === totalScenes && totalScenes > 0;
  const disabled = !allApproved;

  return (
    <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 bg-gradient-to-t from-background/95 via-background/80 to-transparent px-1 pb-3 pt-6">
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">
          Đã duyệt {approvedCount}/{totalScenes} cảnh
        </span>
        {!allApproved && (
          <span className="text-xs text-muted-foreground/70">
            duyệt đủ tất cả cảnh để tiếp tục
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {children}
        <button
          type="button"
          onClick={onSecondaryAction}
          disabled={loading}
          className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          {secondaryLabel}
        </button>
        <button
          type="button"
          onClick={onPrimaryAction}
          disabled={disabled || loading}
          title={disabled && disabledReason ? disabledReason : undefined}
          aria-disabled={disabled || undefined}
          className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-45"
        >
          {loading ? "Đang lưu…" : primaryLabel}
        </button>
      </div>
    </div>
  );
}
