/**
 * TextControl — task 5-2 Step 1: content (bold marker BR-4), role, semantic
 * position (top/center/bottom — no free WYSIWYG drag, per the task's locked
 * decision), and a plain-hex fallback for color/highlight_color.
 *
 * Field names/bounds mirror `TextElement` in backend/app/schemas/scene.py
 * exactly (content maxLength 200, role/position Literals via
 * lib/scene/constants.ts) — this is an editor control for that contract,
 * never a place to invent a new field.
 *
 * Color/highlight rendering is a slot (`renderColorControls`) so ColorPicker
 * (Step 2, with its own contrast-warning logic) can be composed in without
 * this file needing to change again — SceneFormPanel wires the real
 * ColorPicker in Step 6.
 */

"use client";

import { useRef, type ReactNode } from "react";
import { BoldButton, applyBoldToTextarea } from "./BoldButton";
import { TEXT_ROLES, TEXT_POSITIONS, type TextRole, type TextPosition } from "@/lib/scene/constants";

export interface TextControlValue {
  content: string;
  role: TextRole;
  position: TextPosition;
  color?: string | null;
  highlightColor?: string | null;
}

export interface TextControlProps {
  value: TextControlValue;
  onChange: (next: TextControlValue) => void;
  renderColorControls?: (slot: {
    color: string | null | undefined;
    highlightColor: string | null | undefined;
    onColorChange: (hex: string | null) => void;
    onHighlightChange: (hex: string | null) => void;
  }) => ReactNode;
  disabled?: boolean;
}

export function TextControl({ value, onChange, renderColorControls, disabled }: TextControlProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const handleContentChange = (content: string) => onChange({ ...value, content });

  return (
    <div className="space-y-3" aria-label="Điều khiển chữ">
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="text-control-content" className="text-sm font-medium text-foreground">
            Nội dung
          </label>
          <BoldButton
            textareaRef={textareaRef}
            value={value.content}
            onChange={handleContentChange}
            disabled={disabled}
          />
        </div>
        <textarea
          id="text-control-content"
          ref={textareaRef}
          value={value.content}
          disabled={disabled}
          maxLength={200}
          rows={4}
          onChange={(e) => handleContentChange(e.target.value)}
          onKeyDown={(e) => {
            const isBoldShortcut = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b";
            if (isBoldShortcut) {
              e.preventDefault();
              applyBoldToTextarea(textareaRef.current, value.content, handleContentChange);
            }
          }}
          className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="text-control-role" className="mb-1 block text-sm font-medium text-foreground">
            Vai trò
          </label>
          <select
            id="text-control-role"
            value={value.role}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, role: e.target.value as TextRole })}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
          >
            {TEXT_ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="text-control-position" className="mb-1 block text-sm font-medium text-foreground">
            Vị trí
          </label>
          <select
            id="text-control-position"
            value={value.position}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, position: e.target.value as TextPosition })}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
          >
            {TEXT_POSITIONS.map((position) => (
              <option key={position} value={position}>
                {position}
              </option>
            ))}
          </select>
        </div>
      </div>

      {renderColorControls ? (
        renderColorControls({
          color: value.color,
          highlightColor: value.highlightColor,
          onColorChange: (hex) => onChange({ ...value, color: hex }),
          onHighlightChange: (hex) => onChange({ ...value, highlightColor: hex }),
        })
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="text-control-color" className="mb-1 block text-sm font-medium text-foreground">
              Màu chữ
            </label>
            <input
              id="text-control-color"
              type="text"
              value={value.color ?? ""}
              disabled={disabled}
              placeholder="#RRGGBB"
              onChange={(e) => onChange({ ...value, color: e.target.value || null })}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
            />
          </div>
          <div>
            <label htmlFor="text-control-highlight" className="mb-1 block text-sm font-medium text-foreground">
              Màu highlight
            </label>
            <input
              id="text-control-highlight"
              type="text"
              value={value.highlightColor ?? ""}
              disabled={disabled}
              placeholder="#RRGGBB"
              onChange={(e) => onChange({ ...value, highlightColor: e.target.value || null })}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
            />
          </div>
        </div>
      )}
    </div>
  );
}
