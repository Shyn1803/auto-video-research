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
 */

"use client";

import { useCallback, useState } from "react";
import { useWorkspace, type SceneRow } from "@/lib/workspace-context";
import { useAutosave } from "@/lib/hooks/useAutosave";
import { SchemaField, type JsonSchema } from "@/lib/schema-form/generate";
import { StaleConfirmDialog } from "@/components/workspace/StaleConfirmDialog";

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

export function SceneFormPanel() {
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
    </section>
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
