/**
 * PipelineStepper — 5-station workspace navigator.
 *
 * Design-system §3.2 states:
 *   locked / current / done / done-warning ✓⚠ / running / error / stale
 *
 * A11y: <nav aria-label="Tiến trình">, aria-current="step",
 *        ←/→ + Enter keyboard navigation.
 *
 * BR-1: done station click → readonly + "Sửa lại từ đây"
 * BR-2: locked station click → tooltip "Hoàn thành X trước"
 * BR-6: 5 fixed stations — does not accept arbitrary count
 */

"use client";

import { useCallback, useMemo, useState } from "react";
import { useWorkspace, STATIONS, type StepStatus } from "@/lib/workspace-context";

/* ── visual helpers ─────────────────────────────────── */

function classFor(status: StepStatus): string {
  switch (status) {
    case "done":         return "border-status-pass text-status-pass";
    case "done-warning": return "border-status-warn text-status-warn";
    case "current":      return "border-primary text-foreground";
    case "error":        return "border-status-fail text-status-fail";
    case "locked":
    default:             return "border-border text-muted-foreground opacity-50";
  }
}

function iconFor(status: StepStatus): string {
  switch (status) {
    case "done":         return "✓";
    case "done-warning": return "✓⚠";
    case "current":      return "●";
    case "locked":       return "○";
    case "error":        return "✗";
  }
}

/**
 * Task 5-8 AC-2 (stepper half): "●%" badge for a backgrounded run. Same
 * BR-1 rule as RunningState -- `pct === null` renders a plain indeterminate
 * ● (no fabricated number), `0 < pct <= 100` renders "●NN%".
 */
function RunningBadge({ pct }: { pct: number | null }) {
  const isDeterminate = typeof pct === "number" && pct > 0 && pct <= 100;
  return (
    <span
      aria-label={isDeterminate ? `Đang chạy ngầm ${pct}%` : "Đang chạy ngầm"}
      className={`ml-1 text-xs ${isDeterminate ? "" : "motion-safe:animate-pulse"}`}
    >
      ●{isDeterminate ? pct : ""}
      {isDeterminate ? "%" : ""}
    </span>
  );
}

/* ── single station pill ────────────────────────────── */

interface PillProps {
  station: (typeof STATIONS)[number];
  status: StepStatus;
  index: number;
  isCurrent: boolean;
  readonly: boolean;
  warnings: string[];
  onSelect: (idx: number) => void;
  onOpenDone: (idx: number) => void;
  /** Non-null when this station has a run backgrounded via RunningState's "Chạy ngầm". */
  runningPct?: number | null;
}

function Pill({
  station,
  status,
  index,
  isCurrent,
  readonly,
  warnings,
  onSelect,
  onOpenDone,
  runningPct,
}: PillProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const isBackgrounded = runningPct !== undefined;

  if (status === "current") {
    return (
      <div
        aria-current="step"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSelect(index);
        }}
        className={`inline-flex items-center gap-1.5 rounded-full border-2 px-4 py-1.5 text-sm font-medium ring-2 ring-primary/40 ${classFor(status)}`}
      >
        <span aria-hidden="true">{iconFor(status)}</span>
        <span>{station.label}</span>
        {isBackgrounded && <RunningBadge pct={runningPct ?? null} />}
      </div>
    );
  }

  const locked = status === "locked" && !readonly;

  return (
    <button
      type="button"
      // Deliberately NOT the native `disabled` attribute: disabled elements
      // don't fire hover/focus events in browsers, which would silently
      // break the BR-2 tooltip (found via a failing hover test — see
      // memory/project-memory.md). `aria-disabled` + blocking the click
      // handler gives the same non-interactive semantics without losing
      // hover/focus.
      aria-disabled={locked || undefined}
      aria-current={isCurrent ? "step" : undefined}
      onClick={() => {
        if (locked) {
          setTooltipOpen((v) => !v);
          return;
        }
        if (status.startsWith("done")) {
          onOpenDone(index);
        } else {
          onSelect(index);
        }
      }}
      onMouseEnter={() => setTooltipOpen(true)}
      onMouseLeave={() => setTooltipOpen(false)}
      onFocus={() => setTooltipOpen(true)}
      onBlur={() => setTooltipOpen(false)}
      title={
        status === "locked"
          ? `Hoàn thành bước ${STATIONS[Math.max(0, index - 1)]?.label ?? "trước"}`
          : undefined
      }
      className={`relative inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition-colors min-h-[36px] ${classFor(status)} ${
        locked ? "cursor-not-allowed" : "cursor-pointer hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      }`}
    >
      <span aria-hidden="true">{iconFor(status)}</span>
      <span>{station.label}</span>
      {isBackgrounded && <RunningBadge pct={runningPct ?? null} />}

      {/* tooltip for done-warning or locked */}
      {tooltipOpen && (status === "done-warning" || locked) && (
        <span
          role="tooltip"
          className={`absolute left-0 top-full z-50 mt-2 w-72 rounded-lg border p-3 text-xs shadow-xl ${
            status === "done-warning"
              ? "border-status-warn bg-status-warn/10 text-status-warn"
              : "border-border bg-card"
          }`}
        >
          {status === "done-warning" && warnings.length > 0 ? (
            <>
              <p className="mb-1 font-semibold">Cảnh báo:</p>
              <ul className="list-disc space-y-0.5 pl-4">
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </>
          ) : (
            <>Hoàn thành bước {STATIONS[Math.max(0, index - 1)]?.label ?? "trước"} trước</>
          )}
        </span>
      )}
    </button>
  );
}

/* ── main stepper ───────────────────────────────────── */

interface PipelineStepperProps {
  className?: string;
  /**
   * Task 5-8 AC-2 (stepper half): set when the current station's run has
   * been backgrounded via RunningState's "Chạy ngầm" — shows a live ●%/
   * indeterminate badge on that station's pill. `pct: null` = no real
   * fraction yet (BR-1 parity with RunningState/ProjectProgressCard).
   */
  backgroundRun?: { stationIndex: number; pct: number | null } | null;
}

export default function PipelineStepper({ className, backgroundRun }: PipelineStepperProps) {
  const { state, dispatch } = useWorkspace();
  const readonly = state.readonly;

  const stationWarnings = useMemo(() => {
    // derive done-warning from scenes: any unapproved scene with scene-level warnings
    const warningSet = new Set<string>();
    state.scenes.forEach((sc) => {
      if (!sc.approved && sc.warnings.length > 0) {
        sc.warnings.forEach((w) => warningSet.add(w));
      }
    });
    return Array.from(warningSet);
  }, [state.scenes]);

  const handleStationClick = useCallback(
    (index: number) => {
      dispatch({ type: "SET_CURRENT_STATION", index });
    },
    [dispatch],
  );

  const handleOpenDoneStation = useCallback(
    (index: number) => {
      dispatch({ type: "SET_READONLY", v: true });
      dispatch({ type: "SET_CURRENT_STATION", index });
      // Page wires "Edit from here" → confirmStaleDialog
    },
    [dispatch],
  );

  return (
    <nav
      aria-label="Tiến trình"
      className={`flex flex-wrap items-center gap-2 ${className ?? ""}`}
    >
      {STATIONS.map((station, idx) => (
        <Pill
          key={station.key}
          station={station}
          status={state.stationStates[idx]}
          index={idx}
          isCurrent={state.currentStation === idx}
          readonly={readonly}
          warnings={stationWarnings}
          onSelect={handleStationClick}
          onOpenDone={handleOpenDoneStation}
          runningPct={backgroundRun?.stationIndex === idx ? backgroundRun.pct : undefined}
        />
      ))}
    </nav>
  );
}
