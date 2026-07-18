"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/interceptor";
import { Button } from "@/components/ui/button";

type VoiceGender = "female" | "male";
type FormState = "default" | "loading" | "error";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (projectId: string) => void;
}

/** Create-project modal (task 1-3 Step 6): topic required, format 9:16 default
 * + optional 16:9, voice default female + nghe thử (BR-5), focus-trap + ESC. */
export function CreateProjectModal({ open, onClose, onCreated }: Props) {
  const [topic, setTopic] = useState("");
  const [formats, setFormats] = useState<string[]>(["vertical_1080x1920"]);
  const [voiceGender, setVoiceGender] = useState<VoiceGender>("female");
  const [state, setState] = useState<FormState>("default");
  const [error, setError] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const topicInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) return;
    topicInputRef.current?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          "button, input, select, textarea, [tabindex]:not([tabindex='-1'])"
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  const toggleFormat = (fmt: string) => {
    setFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  };

  const playPreview = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const res = await api.get("/projects/preview/tts", {
        params: { voice_gender: voiceGender },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data as Blob);
      if (audioRef.current) {
        audioRef.current.src = url;
        await audioRef.current.play();
      }
    } catch {
      // Non-fatal: preview is a convenience, not a blocker for creating a project.
    } finally {
      setPreviewLoading(false);
    }
  }, [voiceGender]);

  const submit = useCallback(async () => {
    if (!topic.trim()) {
      setError("Chủ đề là bắt buộc");
      return;
    }
    setState("loading");
    setError("");
    try {
      const { data } = await api.post<{ id: string }>("/projects", {
        name: topic.trim(),
        topic: topic.trim(),
        mode: "interactive",
        formats: formats.length > 0 ? formats : ["vertical_1080x1920"],
        voice_gender: voiceGender,
      });
      setState("default");
      onCreated(data.id);
    } catch (err: unknown) {
      setState("error");
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? "Không tạo được dự án — thử lại");
    }
  }, [topic, formats, voiceGender, onCreated]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[8vh]"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
        className="card w-full max-w-[460px] rounded-lg border border-border bg-background p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 id="create-project-title" className="m-0 text-lg font-semibold">
            Tạo dự án mới
          </h3>
          <button
            aria-label="Đóng"
            className="text-muted-foreground"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <label htmlFor="cp-topic" className="text-sm font-medium">
          Chủ đề *
        </label>
        <input
          id="cp-topic"
          ref={topicInputRef}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="VD: GPT-5.5, MCP, LangGraph…"
          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          aria-required="true"
          aria-invalid={!!error}
        />
        <div className="mt-1 text-xs text-muted-foreground">
          AI sẽ tự nghiên cứu nguồn tin về chủ đề này
        </div>

        <label className="mt-3 block text-sm font-medium">Định dạng video</label>
        <div className="mt-1 flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={formats.includes("vertical_1080x1920") ? "default" : "outline"}
            className="flex-1"
            onClick={() => toggleFormat("vertical_1080x1920")}
            aria-pressed={formats.includes("vertical_1080x1920")}
          >
            ▯ Dọc 9:16 (TikTok/Shorts)
          </Button>
          <Button
            type="button"
            size="sm"
            variant={formats.includes("horizontal_1920x1080") ? "default" : "outline"}
            className="flex-1"
            onClick={() => toggleFormat("horizontal_1920x1080")}
            aria-pressed={formats.includes("horizontal_1920x1080")}
          >
            ▭ Ngang 16:9 (YouTube)
          </Button>
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          chọn được cả hai — có thể thêm sau
        </div>

        <label htmlFor="cp-voice" className="mt-3 block text-sm font-medium">
          Giọng đọc mặc định
        </label>
        <div className="mt-1 flex gap-2">
          <select
            id="cp-voice"
            value={voiceGender}
            onChange={(e) => setVoiceGender(e.target.value as VoiceGender)}
            className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          >
            <option value="female">Nữ (Hoài My)</option>
            <option value="male">Nam (Nam Minh)</option>
          </select>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={playPreview}
            disabled={previewLoading}
          >
            {previewLoading ? "…" : "🔊 Nghe thử"}
          </Button>
        </div>
        <audio ref={audioRef} className="hidden">
          <track kind="captions" />
        </audio>

        {error && (
          <div role="alert" className="mt-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <Button
          type="button"
          className="mt-4 w-full justify-center"
          onClick={submit}
          disabled={state === "loading"}
        >
          {state === "loading" ? "Đang tạo…" : "Tạo & bắt đầu nghiên cứu ▸"}
        </Button>
      </div>
    </div>
  );
}
