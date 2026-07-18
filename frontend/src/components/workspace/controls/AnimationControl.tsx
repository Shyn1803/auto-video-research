/**
 * AnimationControl — task 5-2 Step 3.
 *
 * `type` select + `delay_ms` slider, bound to the exact set of
 * Layout-Engine/Motion-Planner-approved animation presets
 * (`Animation.type` in backend/app/schemas/scene.py:74, mirrored in
 * lib/scene/constants.ts — no `packages/remotion-templates/src/motion/presets.ts`
 * data file exists yet, see this task's state-file decision log). This
 * control must never let a user/UI value outside that Literal reach the
 * Scene JSON — that would be an AI/UI-chooses-layout violation
 * (anti-patterns/ai-chooses-layout.md) if it ever leaked into stored content.
 *
 * AC-5 (a11y): the delay slider is a native `<input type="range">`. Real
 * browsers already step it on ←/→, but that native stepping isn't observable
 * in this project's jsdom/happy-dom test environment (verified empirically —
 * a bare keydown never mutates `.value` there), so ←/→ are handled
 * explicitly here with `preventDefault()` to suppress the native default and
 * keep exactly one code path in control of the value cross-environment.
 */

"use client";

import {
  ANIMATION_TYPES,
  ANIMATION_DELAY_MS_MIN,
  ANIMATION_DELAY_MS_MAX,
  ANIMATION_DELAY_MS_STEP,
  type AnimationType,
} from "@/lib/scene/constants";

export interface AnimationControlValue {
  type: AnimationType;
  delayMs: number;
}

export interface AnimationControlProps {
  value: AnimationControlValue;
  onChange: (next: AnimationControlValue) => void;
  disabled?: boolean;
}

const ANIMATION_TYPE_LABELS: Record<AnimationType, string> = {
  none: "Không hiệu ứng (theo Motion Planner)",
  fade_in: "Mờ dần vào",
  slide_up: "Trượt lên",
  slide_left: "Trượt trái",
  zoom_in: "Phóng to vào",
  pop: "Bật nảy",
};

export function AnimationControl({ value, onChange, disabled }: AnimationControlProps) {
  return (
    <div className="space-y-3" aria-label="Điều khiển hiệu ứng">
      <div>
        <label htmlFor="animation-control-type" className="mb-1 block text-sm font-medium text-foreground">
          Kiểu hiệu ứng
        </label>
        <select
          id="animation-control-type"
          value={value.type}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, type: e.target.value as AnimationType })}
          className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
        >
          {ANIMATION_TYPES.map((type) => (
            <option key={type} value={type}>
              {ANIMATION_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="animation-control-delay" className="text-sm font-medium text-foreground">
            Độ trễ (delay)
          </label>
          <span className="text-xs text-muted-foreground" aria-hidden="true">
            {value.delayMs} ms
          </span>
        </div>
        <input
          id="animation-control-delay"
          type="range"
          role="slider"
          min={ANIMATION_DELAY_MS_MIN}
          max={ANIMATION_DELAY_MS_MAX}
          step={ANIMATION_DELAY_MS_STEP}
          value={value.delayMs}
          disabled={disabled}
          aria-valuemin={ANIMATION_DELAY_MS_MIN}
          aria-valuemax={ANIMATION_DELAY_MS_MAX}
          aria-valuenow={value.delayMs}
          aria-valuetext={`${value.delayMs} mili giây`}
          onChange={(e) => onChange({ ...value, delayMs: Number(e.target.value) })}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === "ArrowRight" || e.key === "ArrowUp") {
              e.preventDefault();
              onChange({
                ...value,
                delayMs: Math.min(ANIMATION_DELAY_MS_MAX, value.delayMs + ANIMATION_DELAY_MS_STEP),
              });
            } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
              e.preventDefault();
              onChange({
                ...value,
                delayMs: Math.max(ANIMATION_DELAY_MS_MIN, value.delayMs - ANIMATION_DELAY_MS_STEP),
              });
            }
          }}
          className="w-full accent-primary disabled:opacity-60"
        />
      </div>
    </div>
  );
}
