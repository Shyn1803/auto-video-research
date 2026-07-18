/**
 * SceneFormPanel — column 2 of the Phân cảnh 3-column layout.
 *
 * Schema-driven (BR-4): reads a JSON Schema fixture and uses SchemaField to
 * render controls per field type.  Add an optional field to the schema →
 * zero FE changes.
 *
 * In (5-1): wire the form;controls-wiring (5-2) adds the full prop set.
 * Autosave: useAutosave fires PUT with 1s debounce + offline resilience.
 * 422: field_path → mapped to path in schema via onFieldError.
 *
 * Task 5-2 adds `SceneDetailControls` below the generic form: the real
 * Text/Color/Animation/Layout-dry-run/Voice controls, bound to a per-scene
 * Scene JSON draft (lib/scene/fixture.ts — same no-live-backend dev-server
 * precedent 5-1 established for FIXTURE_SCENES) and PUT via the real
 * `/projects/{id}/scenes/{scene_id}` endpoint (lib/api/scenes.ts).
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useWorkspace, type SceneRow } from "@/lib/workspace-context";
import { useAutosave } from "@/lib/hooks/useAutosave";
import { SchemaField, type JsonSchema } from "@/lib/schema-form/generate";
import { StaleConfirmDialog } from "@/components/workspace/StaleConfirmDialog";
import { TextControl } from "@/components/workspace/controls/TextControl";
import { ColorPicker } from "@/components/workspace/controls/ColorPicker";
import { AnimationControl } from "@/components/workspace/controls/AnimationControl";
import { LayoutDryRunDialog } from "@/components/workspace/controls/LayoutDryRunDialog";
import { VoicePanel } from "@/components/workspace/controls/VoicePanel";
import { checkLayoutChange } from "@/lib/scene/layout-constraints";
import { putScene } from "@/lib/api/scenes";
import { SCENE_FIXTURES } from "@/lib/scene/fixture";
import type { SceneJson } from "@/lib/scene/types";
import { LAYOUT_NAMES, type LayoutName } from "@/lib/scene/layout-names";

interface SceneFormValue {
  title: string;
  body: string;
  layout_cls: string;
  duration_ms: number;
  sticky: boolean;
  extra_tags: string[];
}

const EMPTY_FORM_VALUE: SceneFormValue = {
  title: "",
  body: "",
  layout_cls: "",
  duration_ms: 6000,
  sticky: false,
  extra_tags: [],
};

/* ── schema fixture — mirrors the committed scene-1.0.0.json (2-1) ─ */
const SCENE_SCHEMA: JsonSchema = {
  type: "object",
  properties: {
    title:      { type: "string", title: "Tiêu đề", minLength: 80 },
    body:       { type: "string", title: "Lời đọc (voice-over)", minLength: 500 },
    layout_cls: { type: "string", title: "Bố cục" },
    duration_ms:{ type: "integer", title: "Thời lượng (ms)" },
    sticky:     { type: "boolean", title: "Ghim màn" },
    extra_tags: { type: "array", title: "Tags thêm" },
  },
  required: ["title", "body"],
};

export interface SceneFormPanelProps {
  /** Task 5-2: reports the live-edited Scene JSON draft so the caller
   * (scenes/page.tsx) can feed it straight into ScenePlayerPanel — the
   * Player must reflect edits immediately, not just after the debounced
   * PUT settles (AC-1). */
  onDraftChange?: (scene: SceneJson | null) => void;
}

export function SceneFormPanel({ onDraftChange }: SceneFormPanelProps = {}) {
  const { state, dispatch } = useWorkspace();

  const idx = state.selectedSceneIndex;
  const scene: SceneRow | undefined =
    idx !== null ? state.scenes[idx] : undefined;

  /* --- autosave per scene (debounce 1s, offline safe) ---- */
  const onSave = useCallback(
    async (value: SceneFormValue) => {
      // In 5-1 the save is a placeholder — 5-2 wires the real PUT /api/scenes/{id}
      // The contract change (POST scenes/{id}/approve) lives in Step 6.
      console.log("[SceneFormPanel] autosave", value);
      return Promise.resolve();
    },
    [],
  );

  const { value, setValue, status, manuallySave } = useAutosave<SceneFormValue>({
    save: onSave,
    debounceMs: 1000,
    initialValue: scene
      ? { ...EMPTY_FORM_VALUE, title: scene.title, layout_cls: scene.layoutClass }
      : EMPTY_FORM_VALUE,
  });

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleFieldChange = useCallback(
    (path: string[], next: unknown) => {
      setValue((prev: SceneFormValue) => {
        const copy: Record<string, unknown> = { ...prev };
        let cur: Record<string, unknown> = copy;
        for (let i = 0; i < path.length - 1; i++) {
          const k = path[i];
          cur[k] = { ...(cur[k] as Record<string, unknown> | undefined) };
          cur = cur[k] as Record<string, unknown>;
        }
        const last = path[path.length - 1];
        cur[last] = next;
        // clear error on change
        setFieldErrors((errs) => {
          const n = { ...errs };
          delete n[path.join(".")];
          return n;
        });
        dispatch({ type: "SET_UNSAVED", v: true });
        return copy as unknown as SceneFormValue;
      });
    },
    [dispatch, setValue],
  );

  /* return early if nothing selected */
  if (!scene) {
    return (
      <section
        aria-label="Form phân cảnh"
        className="flex-1 rounded-xl border border-border bg-card p-4"
      >
        <p className="text-sm text-muted-foreground">
          Chọn một phân cảnh để chỉnh sửa
        </p>
      </section>
    );
  }

  const saveBadge = (() => {
    switch (status) {
      case "saved":   return { kind: "pass" as const, text: "Đã lưu ✓" };
      case "saving":  return { kind: "run"  as const, text: "Đang lưu…" };
      case "error":   return { kind: "fail" as const, text: "Lỗi lưu" };
      case "offline": return { kind: "warn" as const, text: "⚠ chưa lưu" };
    }
  })();

  return (
    <section
      aria-label="Form phân cảnh"
      className="flex-1 space-y-4 rounded-xl border border-border bg-card p-4"
    >
      {/*Autosave badge — BR-3 */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-foreground">
          Cảnh #{state.scenes.indexOf(scene) + 1}
        </h3>
        <SaveBadge {...saveBadge} onRetry={manuallySave} />
      </div>

      {/*
        Readonly banner — BR-1.
        The Stepper sets store.readonly = true when a done station is opened;
        this banner is then shown and fields are disabled.
      */}
      {state.readonly && (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-muted p-3">
          <span aria-hidden="true">👁</span>
          <span className="text-sm text-muted-foreground">
            Chế độ xem lại — bước này đã duyệt. Nội dung chỉ đọc.
          </span>
          <EditFromHereButton />
        </div>
      )}

      {/* Schema-driven form — AC-4 */}
      <SchemaField
        path={[]}
        schema={SCENE_SCHEMA}
        value={value}
        onChange={handleFieldChange}
        fieldErrors={fieldErrors}
      />

      {/* Task 5-2: text/color/animation/layout-dry-run/voice controls,
          keyed by scene id so switching the selected scene remounts this
          section's draft state instead of leaking the previous scene's edits. */}
      <SceneDetailControls
        key={scene.id}
        projectId={state.projectId}
        sceneId={scene.id}
        disabled={state.readonly}
        onDraftChange={onDraftChange}
      />
    </section>
  );
}

/* ── task 5-2: real edit controls, bound to a per-scene Scene JSON draft ── */

function SceneDetailControls({
  projectId,
  sceneId,
  disabled,
  onDraftChange,
}: {
  projectId: string;
  sceneId: string;
  disabled?: boolean;
  onDraftChange?: (scene: SceneJson | null) => void;
}) {
  const fixture = SCENE_FIXTURES[sceneId];

  const onSaveDraft = useCallback(
    async (next: SceneJson) => {
      // Real endpoint is called; a sandbox/dev environment without a live
      // backend will surface this as useAutosave's existing offline/error
      // path (BR-3) rather than crashing the form.
      await putScene(projectId, sceneId, next);
    },
    [projectId, sceneId],
  );

  const { value: draft, setValue: setDraft, status, manuallySave } = useAutosave<SceneJson | null>(
    {
      save: async (v) => {
        if (v) await onSaveDraft(v);
      },
      debounceMs: 1000,
      initialValue: fixture ?? null,
    },
  );

  // Report every draft change immediately (not debounced) — AC-1 "Player
  // reflects ngay".
  useEffect(() => {
    onDraftChange?.(draft);
    // Only wants to fire on draft changes, not on identity change of the callback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  // BR-3: capture the voice text baseline the produced audio corresponds to,
  // exactly once per scene (on first load), so later edits can be compared
  // against it. Scene JSON itself has no separate "text at produce time"
  // field — this control is the one place that tracks it client-side.
  const producedAudioTextRef = useRef<string | null>(null);
  if (producedAudioTextRef.current === null && draft?.voice?.audio) {
    producedAudioTextRef.current = draft.voice.text;
  }

  const [activeTextIndex, setActiveTextIndex] = useState(0);
  const [pendingLayout, setPendingLayout] = useState<LayoutName | null>(null);

  if (!draft) {
    return (
      <p className="text-sm text-muted-foreground">
        Không có dữ liệu chi tiết cho cảnh này (fixture chưa có).
      </p>
    );
  }

  const activeText = draft.texts[activeTextIndex];

  const applyLayout = (nextLayout: LayoutName) => {
    setDraft((prev) => (prev ? { ...prev, layout: nextLayout } : prev));
  };

  const handleLayoutSelect = (nextLayout: LayoutName) => {
    const result = checkLayoutChange(draft.texts, draft.images.length, nextLayout);
    if (result.ok) {
      applyLayout(nextLayout);
    } else {
      setPendingLayout(nextLayout);
    }
  };

  return (
    <div className="space-y-4 border-t border-border pt-4">
      <h4 className="text-sm font-semibold text-foreground">Chỉnh sửa chi tiết</h4>

      {/* Layout select + dry-run (BR-1) */}
      <div>
        <label htmlFor="scene-detail-layout" className="mb-1 block text-sm font-medium text-foreground">
          Bố cục
        </label>
        <select
          id="scene-detail-layout"
          value={draft.layout}
          disabled={disabled}
          onChange={(e) => handleLayoutSelect(e.target.value as LayoutName)}
          className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
        >
          {LAYOUT_NAMES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <LayoutDryRunDialog
          open={pendingLayout !== null}
          fromLayout={draft.layout}
          toLayout={pendingLayout ?? ""}
          texts={draft.texts}
          imagesCount={draft.images.length}
          onCancel={() => setPendingLayout(null)}
          onConfirm={() => {
            if (pendingLayout) applyLayout(pendingLayout);
            setPendingLayout(null);
          }}
        />
      </div>

      {/* Text element picker (a scene may have multiple texts) */}
      {draft.texts.length > 1 && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Chọn phần tử chữ">
          {draft.texts.map((t, i) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTextIndex(i)}
              aria-pressed={i === activeTextIndex}
              className={`rounded-full border px-2.5 py-0.5 text-xs ${
                i === activeTextIndex
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground"
              }`}
            >
              {t.id}
            </button>
          ))}
        </div>
      )}

      {activeText && (
        <>
          <TextControl
            value={{
              content: activeText.content,
              role: activeText.role,
              position: activeText.position,
              color: activeText.color,
              highlightColor: activeText.highlight_color,
            }}
            disabled={disabled}
            onChange={(next) =>
              setDraft((prev) => {
                if (!prev) return prev;
                const texts = prev.texts.map((t, i) =>
                  i === activeTextIndex
                    ? {
                        ...t,
                        content: next.content,
                        role: next.role,
                        position: next.position,
                        color: next.color,
                        highlight_color: next.highlightColor,
                      }
                    : t,
                );
                return { ...prev, texts };
              })
            }
            renderColorControls={({ color, highlightColor, onColorChange, onHighlightChange }) => (
              <div className="grid grid-cols-2 gap-3">
                <ColorPicker
                  label="Màu chữ"
                  value={color}
                  onChange={onColorChange}
                  backgroundColor={draft.background && "color" in draft.background ? (draft.background.color as string) : undefined}
                  disabled={disabled}
                />
                <ColorPicker
                  label="Màu highlight"
                  value={highlightColor}
                  onChange={onHighlightChange}
                  backgroundColor={draft.background && "color" in draft.background ? (draft.background.color as string) : undefined}
                  disabled={disabled}
                />
              </div>
            )}
          />

          <AnimationControl
            value={{
              type: activeText.animation?.type ?? "none",
              delayMs: activeText.animation?.delay_ms ?? 0,
            }}
            disabled={disabled}
            onChange={(next) =>
              setDraft((prev) => {
                if (!prev) return prev;
                const texts = prev.texts.map((t, i) =>
                  i === activeTextIndex
                    ? {
                        ...t,
                        animation: {
                          type: next.type,
                          delay_ms: next.delayMs,
                          duration_ms: t.animation?.duration_ms ?? 400,
                        },
                      }
                    : t,
                );
                return { ...prev, texts };
              })
            }
          />
        </>
      )}

      {draft.voice && (
        <VoicePanel
          value={{
            text: draft.voice.text,
            voiceId: draft.voice.voice_id,
            speed: draft.voice.speed,
          }}
          disabled={disabled}
          hasProducedAudio={Boolean(draft.voice.audio)}
          producedAudioText={producedAudioTextRef.current ?? draft.voice.text}
          onChange={(next) =>
            setDraft((prev) =>
              prev && prev.voice
                ? { ...prev, voice: { ...prev.voice, text: next.text, voice_id: next.voiceId, speed: next.speed } }
                : prev,
            )
          }
        />
      )}

      <div aria-live="polite" className="text-xs text-muted-foreground">
        {status === "saving" && "Đang lưu chi tiết…"}
        {status === "saved" && "Đã lưu chi tiết ✓"}
        {status === "offline" && (
          <button type="button" onClick={manuallySave} className="underline">
            ⚠ chưa lưu — thử lại
          </button>
        )}
        {status === "error" && (
          <button type="button" onClick={manuallySave} className="underline text-status-fail">
            Lỗi lưu — thử lại
          </button>
        )}
      </div>
    </div>
  );
}

/* ── small sub-components ────────────────────────────── */

function SaveBadge({
  kind,
  text,
  onRetry,
}: {
  kind: "pass" | "run" | "fail" | "warn";
  text: string;
  onRetry: () => Promise<void>;
}) {
  const [retrying, setRetrying] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        if (kind === "warn" || kind === "fail") {
          setRetrying(true);
          await onRetry();
          setRetrying(false);
        }
      }}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        kind === "pass" && "border-status-pass/40 bg-status-pass/10 text-status-pass"
      } ${kind === "run"  && "border-status-run/40 bg-status-run/10 text-status-run"}
        ${kind === "fail" && "border-status-fail/40 bg-status-fail/10 text-status-fail"}
        ${kind === "warn" && "border-status-warn/40 bg-status-warn/10 text-status-warn"}
      `}
      aria-live="polite"
    >
      {retrying ? "Đang thử lại…" : text}
    </button>
  );
}

function EditFromHereButton() {
  const { state, dispatch } = useWorkspace();
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setConfirmOpen(true)}
        className="ml-auto rounded-lg border border-border bg-card px-3 py-1.5 text-sm transition-colors hover:bg-muted"
      >
        Sửa lại từ đây
      </button>
      <StaleConfirmDialog
        open={confirmOpen}
        fromIndex={state.currentStation}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          dispatch({ type: "SET_READONLY", v: false });
        }}
      />
    </>
  );
}
