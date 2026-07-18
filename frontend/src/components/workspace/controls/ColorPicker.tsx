/**
 * ColorPicker — task 5-2 Step 2, BR-2.
 *
 * Theme-preset swatches + a custom hex input. A custom hex that reads poorly
 * against the scene background triggers a **non-blocking** contrast warning
 * (BR-2: "cảnh báo contrast (không chặn)") — `onChange` still fires either way,
 * this control only ever *informs*, never rejects a save.
 *
 * Contrast math comes from `wcag-contrast` (npm) per the task's explicit
 * instruction not to hand-roll WCAG contrast math (Test Notes / DoD).
 */

"use client";

import { useMemo, useState } from "react";
import { hex as contrastHex, score as contrastScore } from "wcag-contrast";

const HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

/** WCAG AA minimum ratio for normal-size text. */
const AA_NORMAL_TEXT_THRESHOLD = 4.5;

/** Curated preset swatches shown above the custom hex input. Distinct from
 * the app's own oklch-based CSS theme tokens (globals.css) — these are
 * literal hex values because `TextElement.color`/`highlight_color` in the
 * Scene JSON contract are hex strings (scene.py:86-87), not CSS variables. */
export const DEFAULT_COLOR_PRESETS: readonly string[] = [
  "#FFFFFF",
  "#0F172A",
  "#F59E0B",
  "#22C55E",
  "#EF4444",
  "#3B82F6",
  "#A855F7",
  "#EC4899",
];

export interface ColorPickerProps {
  label: string;
  /** Current hex value, or null/undefined for "unset" (planner-default). */
  value: string | null | undefined;
  onChange: (hex: string | null) => void;
  /** The color this value will be rendered against — used for the contrast
   * check only; defaults to the schema example's dark scene background. */
  backgroundColor?: string;
  presets?: readonly string[];
  disabled?: boolean;
}

export function ColorPicker({
  label,
  value,
  onChange,
  backgroundColor = "#0F172A",
  presets = DEFAULT_COLOR_PRESETS,
  disabled,
}: ColorPickerProps) {
  const [customHex, setCustomHex] = useState(value ?? "");

  const contrast = useMemo(() => {
    const candidate = value && HEX_PATTERN.test(value) ? value : null;
    if (!candidate || !HEX_PATTERN.test(backgroundColor)) return null;
    const ratio = contrastHex(candidate, backgroundColor);
    return { ratio, label: contrastScore(ratio) };
  }, [value, backgroundColor]);

  const showContrastWarning = contrast !== null && contrast.ratio < AA_NORMAL_TEXT_THRESHOLD;

  const commitCustomHex = (raw: string) => {
    setCustomHex(raw);
    if (raw === "") {
      onChange(null);
      return;
    }
    const normalized = raw.startsWith("#") ? raw : `#${raw}`;
    // Always forward the value — BR-2 is explicit that contrast is a warning,
    // never a save-blocker. Malformed hex still gets passed through; the
    // Scene JSON PUT's server-side schema validation is the real gate.
    onChange(normalized);
  };

  return (
    <div className="space-y-2">
      <span className="block text-sm font-medium text-foreground">{label}</span>

      <div className="flex flex-wrap gap-2" role="group" aria-label={`${label} — preset`}>
        {presets.map((preset) => (
          <button
            key={preset}
            type="button"
            disabled={disabled}
            aria-label={preset}
            aria-pressed={value?.toUpperCase() === preset.toUpperCase()}
            onClick={() => {
              setCustomHex(preset);
              onChange(preset);
            }}
            style={{ backgroundColor: preset }}
            className={`size-7 rounded-full border-2 transition-transform hover:scale-110 disabled:opacity-50 ${
              value?.toUpperCase() === preset.toUpperCase() ? "border-primary" : "border-border"
            }`}
          />
        ))}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          aria-label={`${label} — mã hex tuỳ chỉnh`}
          value={customHex}
          disabled={disabled}
          placeholder="#RRGGBB"
          onChange={(e) => commitCustomHex(e.target.value)}
          className="w-28 rounded-lg border border-border bg-muted px-2 py-1 text-sm"
        />
        {value && HEX_PATTERN.test(value) && (
          <span
            aria-hidden="true"
            className="size-6 rounded border border-border"
            style={{ backgroundColor: value }}
          />
        )}
      </div>

      {showContrastWarning && (
        <p role="alert" className="flex items-center gap-1 text-xs text-status-warn">
          ⚠ Độ tương phản thấp ({contrast!.ratio.toFixed(1)}:1, {contrast!.label}) — chữ có thể khó
          đọc trên nền này. Vẫn có thể lưu.
        </p>
      )}
    </div>
  );
}
