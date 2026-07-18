/**
 * Frontend mirror of the Literal enums in `backend/app/schemas/scene.py` —
 * the Scene JSON render contract's single source of truth
 * (CLAUDE.md §9, rules/type-safety.md "one schema source").
 *
 * These values must never diverge from scene.py's Literals and a control
 * built on top of this file must never invent a value outside this list —
 * doing so would leak an AI/UI-chosen layout/animation value into the
 * render contract (anti-patterns/ai-chooses-layout.md). If scene.py's
 * Literal changes, update this file in the same PR ("đổi contract",
 * dev-guide.md §5 / rules/documentation.md).
 */

/** TextElement.role — backend scene.py:84 */
export const TEXT_ROLES = ["heading", "body", "caption", "stat"] as const;
export type TextRole = (typeof TEXT_ROLES)[number];

/** TextElement.position — semantic position only, no free WYSIWYG drag
 * (locked decision, task 5-2 "Decisions already locked"). backend scene.py:85 */
export const TEXT_POSITIONS = ["top", "center", "bottom"] as const;
export type TextPosition = (typeof TEXT_POSITIONS)[number];

/**
 * Animation.type — backend scene.py:74. These are the only
 * Layout-Engine/Motion-Planner-approved animation presets; a UI control may
 * only pick among them (AnimationControl.tsx), never define a new one.
 */
export const ANIMATION_TYPES = [
  "none",
  "fade_in",
  "slide_up",
  "slide_left",
  "zoom_in",
  "pop",
] as const;
export type AnimationType = (typeof ANIMATION_TYPES)[number];

/** Animation.delay_ms bounds — backend scene.py:75 */
export const ANIMATION_DELAY_MS_MIN = 0;
export const ANIMATION_DELAY_MS_MAX = 5000;
export const ANIMATION_DELAY_MS_STEP = 100;

/** Animation.duration_ms bounds — backend scene.py:76 */
export const ANIMATION_DURATION_MS_MIN = 100;
export const ANIMATION_DURATION_MS_MAX = 2000;

/** VoiceSpec.speed bounds — backend scene.py:123 */
export const VOICE_SPEED_MIN = 0.8;
export const VOICE_SPEED_MAX = 1.3;
export const VOICE_SPEED_STEP = 0.05;

/** Giọng nam/nữ voice_id options — placeholder catalog until a real TTS
 * adapter voice-list endpoint exists (3-x epic); values are opaque voice_ids
 * passed through unchanged, not layout/content decisions. */
export const VOICE_OPTIONS = [
  { id: "vi-VN-male-1", label: "Giọng nam" },
  { id: "vi-VN-female-1", label: "Giọng nữ" },
] as const;
