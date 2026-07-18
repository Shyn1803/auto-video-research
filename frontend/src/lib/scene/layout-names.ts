/**
 * Mirrors `LayoutName` in backend/app/schemas/scene.py:12-24 — the 11-class
 * v1 layout catalog (docs/specs/scene-json-schema.md §2). `layout` is always
 * the Layout Classifier's output; a user only ever sets `layout_override`
 * (layout-engine.md §5.1) — this control lets the editor pick among the
 * same fixed catalog, never a value outside it.
 */
export const LAYOUT_NAMES = [
  "Hero",
  "TextFocus",
  "MediaFull",
  "MediaText",
  "Comparison",
  "BigNumber",
  "Chart",
  "VersusTable",
  "List",
  "Quote",
  "Code",
] as const;

export type LayoutName = (typeof LAYOUT_NAMES)[number];
