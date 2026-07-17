"use client";

import { useState } from "react";
import { api } from "@/lib/api/interceptor";

type Gender = "female" | "male";

export default function AssetsPage() {
  const [gender, setGender] = useState<Gender>("female");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState<number | null>(null);

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    setAudioUrl(null);
    setDurationMs(null);
    try {
      const res = await api.get("/projects/preview/tts", {
        params: { voice_gender: gender },
        responseType: "blob",
      });
      const url = URL.createObjectURL(
        new Blob([res.data], { type: "audio/mpeg" }),
      );
      setAudioUrl(url);
      setDurationMs(Number(res.headers["x-duration-ms"] ?? 0));
    } catch {
      setError("Không thể phát âm thanh mẫu. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Tài sản — Giọng đọc mẫu</h1>
      <p className="mt-1 text-sm text-slate-400">
        Nghe thử giọng đọc tiếng Việt trước khi tạo dự án.
      </p>

      <div className="mt-6 flex items-center gap-4">
        <label className="text-sm text-slate-300" htmlFor="gender">
          Giọng
        </label>
        <select
          id="gender"
          value={gender}
          onChange={(e) => setGender(e.target.value as Gender)}
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-50"
        >
          <option value="female">Nữ (Hoài My)</option>
          <option value="male">Nam (Nam Minh)</option>
        </select>

        <button
          type="button"
          onClick={handlePreview}
          disabled={loading}
          className="rounded-md bg-cyan-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Đang tạo…" : "Phát thử"}
        </button>
      </div>

      {error && (
        <p className="mt-4 text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      {audioUrl && (
        <div className="mt-6">
          <audio
            controls
            autoPlay
            src={audioUrl}
            className="w-full"
            onEnded={() => {
              URL.revokeObjectURL(audioUrl);
              setAudioUrl(null);
            }}
          />
          {durationMs != null && (
            <p className="mt-1 text-xs text-slate-500">
              Thời lượng: {(durationMs / 1000).toFixed(1)}s
            </p>
          )}
        </div>
      )}
    </main>
  );
}
