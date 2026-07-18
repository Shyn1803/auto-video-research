/**
 * SceneSidebar — column 1 of the Phân cảnh 3-column layout.
 *
 * Shows thumbnails: scene number, layout icon, badge (✓/⚠/✗).
 * Row actions: keyboard ↑/↓ to move (5-4), + Thêm cảnh placeholder.
 */

"use client";

import { useWorkspace } from "@/lib/workspace-context";
import { StatusBadge } from "@/components/ui/status-badge";

const LAYOUT_ICONS: Record<string, string> = {
  Hero: "▣", TextFocus: "Aa", MediaFull: "🖼", MediaText: "■+📝",
  Comparison: "A|B", BigNumber: "92%", Chart: "▂▅▇",
  VersusTable: "vs", List: "•••", Quote: "❝", Code: "</>",
};

export function SceneSidebar() {
  const { state, dispatch } = useWorkspace();

  return (
    <aside className="w-44 shrink-0 space-y-2" aria-label="Danh sách phân cảnh">
      {state.scenes.map((sc, idx) => {
        const sel = state.selectedSceneIndex === idx;
        const icon = LAYOUT_ICONS[sc.layoutClass] ?? "▣";

        return (
          <button
            type="button"
            key={sc.id}
            onClick={() => dispatch({ type: "SELECT_SCENE", index: idx })}
            className={`w-full rounded-lg border p-2 text-left text-sm transition-colors ${
              sel
                ? "border-primary bg-primary/10"
                : "border-border bg-card hover:border-primary/50"
            }`}
            aria-current={sel ? "true" : undefined}
          >
            <div className="flex items-center gap-1">
              <span className="text-xs font-mono">{icon}</span>
              <span className="truncate">
                #{idx + 1} {sc.title}
              </span>
            </div>
            <div className="mt-1">
              <StatusBadge
                kind={sc.approved ? "pass" : "warn"}
                label={sc.approved ? "✓" : "⚠ đang sửa"}
                className="!px-1.5 !py-0 !text-[10px]"
              />
            </div>
          </button>
        );
      })}

      {/* Add scene placeholder — 5-4 wires */}
      <button
        type="button"
        className="flex w-full items-center justify-center rounded-lg border border-dashed border-border p-2 text-xs text-muted-foreground hover:border-primary hover:text-primary"
      >
        + Thêm cảnh
      </button>

      <p className="px-1 text-[11px] leading-tight text-muted-foreground/70">
        kéo-thả sắp ×ếp · <kbd className="rounded border border-border px-1">↑</kbd>
        <kbd className="ml-1 rounded border border-border px-1">↓</kbd>
      </p>
    </aside>
  );
}
