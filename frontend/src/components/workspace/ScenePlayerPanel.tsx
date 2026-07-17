/**
 * ScenePlayerPanel — column 3 of the Phân cảnh 3-column layout.
 *
 * Wraps `@remotion/player` via the existing `ScenePlayer` component
 * (already in `scene-player/`).  Per CLAUDE.md §9:
 *   "packages/remotion-templates/ is shared source... one implementation"
 *
 * In 5-1 we add the panel shell + 9:16 preview frame + transport controls.
 * Per wireframe §Tầng 2: aspect-ratio 9/16, max-height 400px, play/listen stub.
 */

"use client";

import type { ComponentType } from "react";

// Re-use what was already scaffolded in story 2-2
import { ScenePlayer } from "@/components/scene-player/ScenePlayer";

/* ── fixture input type — mirrors packages/remotion-templates ─ */
export interface ScenePreviewInput {
  duration_ms: number;
  format?: "vertical_1080x1920" | "horizontal_1920x1080";
  voice?: { audio?: unknown } | null;
  [key: string]: unknown;
}

export function ScenePlayerPanel({
  component,
  scene,
}: {
  component: ComponentType<ScenePreviewInput>;
  scene?: ScenePreviewInput;
}) {
  const isEmpty = !scene || !component;

  return (
    <aside
      className="flex-1"
      aria-label="Xem trước phân cảnh"
    >
      <div className="flex flex-col items-center gap-3">
        {/* 9:16 preview frame per wireframe */}
        <div className="w-full max-w-[380px] rounded-xl border border-border bg-black">
          {isEmpty ? (
            <div className="flex h-64 flex-col items-center justify-center gap-2 text-muted-foreground">
              <span>▶</span>
              <span className="text-sm">Chọn cảnh để xem trước</span>
            </div>
          ) : (
            <ScenePlayer component={component} scene={scene} />
          )}
        </div>

        {/* Transport controls — stub; 5-2 adds detail */}
        <div className="flex w-full max-w-[380px] items-center justify-center gap-2">
          <PlayButton />
          <ListenButton />
          <span className="text-xs text-muted-foreground" aria-live="off">
            0:00/0:00
          </span>
        </div>
      </div>
    </aside>
  );
}

function PlayButton() {
  return (
    <button
      type="button"
      className="rounded-lg border border-border bg-muted px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      ▶ Phát
    </button>
  );
}

function ListenButton() {
  return (
    <button
      type="button"
      className="rounded-lg border border-border bg-muted px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      🔊 Nghe giọng
    </button>
  );
}
