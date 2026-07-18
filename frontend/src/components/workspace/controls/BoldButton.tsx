/**
 * BoldButton — BR-4 "bấm B" bold-marker insertion.
 *
 * The Scene JSON `TextElement.content` supports `**bold**` markdown-style
 * markers (scene-json-schema.md §3.2), but a Content Creator should never
 * have to type `**` manually (BR-4). This button (and the `Ctrl+B` shortcut
 * wired alongside it in TextControl.tsx) inserts the marker around the
 * current textarea selection — or an empty `****` pair with the cursor
 * placed in the middle when nothing is selected.
 */

"use client";

import { useCallback, type RefObject } from "react";

export interface BoldMarkerResult {
  text: string;
  selectionStart: number;
  selectionEnd: number;
}

/** Pure function — no DOM access, fully unit-testable. */
export function applyBoldMarker(
  text: string,
  selectionStart: number,
  selectionEnd: number,
): BoldMarkerResult {
  const start = Math.max(0, Math.min(selectionStart, selectionEnd));
  const end = Math.max(0, Math.max(selectionStart, selectionEnd));
  const before = text.slice(0, start);
  const selected = text.slice(start, end);
  const after = text.slice(end);

  if (selected.length === 0) {
    const next = `${before}****${after}`;
    const cursor = start + 2;
    return { text: next, selectionStart: cursor, selectionEnd: cursor };
  }

  const next = `${before}**${selected}**${after}`;
  return {
    text: next,
    selectionStart: start + 2,
    selectionEnd: end + 2,
  };
}

/** Shared by BoldButton's onClick and TextControl's Ctrl+B keydown handler
 * so both paths apply the exact same selection-aware logic. */
export function applyBoldToTextarea(
  el: HTMLTextAreaElement | null,
  value: string,
  onChange: (next: string) => void,
): void {
  const start = el?.selectionStart ?? value.length;
  const end = el?.selectionEnd ?? value.length;
  const result = applyBoldMarker(value, start, end);
  onChange(result.text);
  // Selection is lost once the value re-renders — restore it next frame.
  requestAnimationFrame(() => {
    el?.focus();
    el?.setSelectionRange(result.selectionStart, result.selectionEnd);
  });
}

export interface BoldButtonProps {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
}

export function BoldButton({ textareaRef, value, onChange, disabled }: BoldButtonProps) {
  const handleClick = useCallback(() => {
    applyBoldToTextarea(textareaRef.current, value, onChange);
  }, [textareaRef, value, onChange]);

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      aria-label="In đậm chữ đã chọn (Ctrl+B)"
      title="In đậm (Ctrl+B)"
      className="rounded-lg border border-border bg-muted px-2 py-1 text-xs font-bold leading-none text-foreground transition-colors hover:bg-accent disabled:opacity-50"
    >
      B
    </button>
  );
}
