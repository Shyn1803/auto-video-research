/**
 * LayoutPickerMenu — Task 5-4 Step 3.
 *
 * Canonical PascalCase layout classes only (rules/naming.md) — never the old
 * snake_case names (title_card, full_text, ...), that drift already happened
 * once (postmortems/2026-07-pascalcase-layout-drift.md).
 *
 * Fully keyboard operable (AC-4): ArrowUp/ArrowDown move focus, Enter/Space
 * selects, Escape closes without selecting.
 */

"use client";

import { useEffect, useRef, useState } from "react";

export const LAYOUT_CLASSES = [
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

export type LayoutClass = (typeof LAYOUT_CLASSES)[number];

export const LAYOUT_ICONS: Record<string, string> = {
  Hero: "▣",
  TextFocus: "Aa",
  MediaFull: "🖼",
  MediaText: "■+📝",
  Comparison: "A|B",
  BigNumber: "92%",
  Chart: "▂▅▇",
  VersusTable: "vs",
  List: "•••",
  Quote: "❝",
  Code: "</>",
};

export interface LayoutPickerMenuProps {
  onSelect: (layout: LayoutClass) => void;
  onClose: () => void;
}

export function LayoutPickerMenu({ onSelect, onClose }: LayoutPickerMenuProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    itemRefs.current[activeIndex]?.focus();
  }, [activeIndex]);

  return (
    <div
      role="menu"
      aria-label="Chọn bố cục cho cảnh mới"
      className="absolute z-10 mt-1 w-48 rounded-lg border border-border bg-card p-1 shadow-lg"
      onKeyDown={(e) => {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setActiveIndex((i) => (i + 1) % LAYOUT_CLASSES.length);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setActiveIndex((i) => (i - 1 + LAYOUT_CLASSES.length) % LAYOUT_CLASSES.length);
        } else if (e.key === "Escape") {
          e.preventDefault();
          onClose();
        }
      }}
    >
      {LAYOUT_CLASSES.map((layout, i) => (
        <button
          key={layout}
          ref={(el) => {
            itemRefs.current[i] = el;
          }}
          type="button"
          role="menuitem"
          tabIndex={i === activeIndex ? 0 : -1}
          onClick={() => onSelect(layout)}
          className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-foreground hover:bg-muted focus:bg-muted focus:outline-none"
        >
          <span className="w-8 shrink-0 text-center font-mono text-xs text-muted-foreground">
            {LAYOUT_ICONS[layout]}
          </span>
          {layout}
        </button>
      ))}
    </div>
  );
}
