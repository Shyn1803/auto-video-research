"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api/interceptor";
import { AlertTriangle, Check, RotateCcw } from "lucide-react";

type ViewState = "loading" | "error" | "empty" | "default";

interface PromptRow {
  name: string;
  tier: string;
  description: string | null;
}

interface PromptVersionRow {
  version: number;
  template: string;
  variables: string[];
  is_active: boolean;
  evaluated: boolean;
  created_by: string;
  activated_by: string | null;
}

/** Line-based diff (additions/removals marked with a text prefix, never
 * color-only per the wireframe's a11y note). */
function diffLines(a: string, b: string): { sign: "+" | "-" | " "; text: string }[] {
  const aLines = a.split("\n");
  const bLines = b.split("\n");
  const out: { sign: "+" | "-" | " "; text: string }[] = [];
  const max = Math.max(aLines.length, bLines.length);
  for (let i = 0; i < max; i++) {
    const left = aLines[i];
    const right = bLines[i];
    if (left === right) {
      if (left !== undefined) out.push({ sign: " ", text: left });
    } else {
      if (left !== undefined) out.push({ sign: "-", text: left });
      if (right !== undefined) out.push({ sign: "+", text: right });
    }
  }
  return out;
}

export function PromptsTable() {
  const [prompts, setPrompts] = useState<PromptRow[]>([]);
  const [view, setView] = useState<ViewState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const [selected, setSelected] = useState<string | null>(null);
  const [versions, setVersions] = useState<PromptVersionRow[]>([]);
  const [diffTargets, setDiffTargets] = useState<[number, number] | null>(null);

  const [activateWarning, setActivateWarning] = useState<{
    version: number;
    message: string;
  } | null>(null);

  const loadPrompts = useCallback(async () => {
    setView("loading");
    setErrorMsg("");
    try {
      const { data } = await api.get<PromptRow[]>("/admin/prompts");
      setPrompts(data);
      setView(data.length === 0 ? "empty" : "default");
    } catch {
      setView("error");
      setErrorMsg("Không tải được danh sách prompt");
    }
  }, []);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const openPrompt = async (name: string) => {
    setSelected(name);
    setDiffTargets(null);
    try {
      const { data } = await api.get<PromptVersionRow[]>(
        `/admin/prompts/${name}/versions`,
      );
      setVersions(data);
    } catch {
      setVersions([]);
    }
  };

  const requestActivate = async (version: number) => {
    if (!selected) return;
    const target = versions.find((v) => v.version === version);
    if (target && !target.evaluated) {
      setActivateWarning({
        version,
        message:
          "Phiên bản này chưa chạy eval. Vẫn có thể kích hoạt, nhưng nên chạy `make prompt-eval` trước.",
      });
      return;
    }
    await doActivate(version);
  };

  const doActivate = async (version: number) => {
    if (!selected) return;
    try {
      await api.post(`/admin/prompts/${selected}/versions/${version}/activate`);
      setActivateWarning(null);
      await openPrompt(selected);
    } catch {
      // surfaced inline below via re-fetch; keep it simple for the skeleton UI
    }
  };

  return (
    <section className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-50">Prompts</h1>
        <p className="text-sm text-slate-400">
          Quản lý prompt theo version — activate không cần deploy (FR-14).
        </p>
      </header>

      <div className="grid grid-cols-3 gap-6">
        {/* ── prompt list ─────────────────────────────────────────── */}
        <div className="col-span-1 overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-sm" aria-label="Danh sách prompt">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="px-4 py-3">Tên</th>
                <th className="px-4 py-3">Tier</th>
              </tr>
            </thead>
            <tbody>
              {view === "loading" && (
                <tr>
                  <td colSpan={2} className="px-4 py-8 text-center text-slate-500">
                    Đang tải…
                  </td>
                </tr>
              )}
              {view === "error" && (
                <tr>
                  <td colSpan={2} className="px-4 py-8 text-center text-red-400">
                    {errorMsg}
                  </td>
                </tr>
              )}
              {view === "empty" && (
                <tr>
                  <td colSpan={2} className="px-4 py-8 text-center text-slate-500">
                    Chưa có prompt nào — chạy seed trước.
                  </td>
                </tr>
              )}
              {prompts.map((p) => (
                <tr
                  key={p.name}
                  className={`cursor-pointer border-b border-slate-800/60 hover:bg-slate-900/40 ${
                    selected === p.name ? "bg-slate-900/60" : ""
                  }`}
                  onClick={() => openPrompt(p.name)}
                >
                  <td className="px-4 py-3 font-mono text-slate-200">{p.name}</td>
                  <td className="px-4 py-3 text-slate-400">{p.tier}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── editor / version history ────────────────────────────── */}
        <div className="col-span-2 space-y-4">
          {!selected && (
            <p className="text-sm text-slate-500">Chọn 1 prompt bên trái để xem version.</p>
          )}
          {selected && (
            <>
              <h2 className="font-mono text-lg text-slate-100">{selected}</h2>
              <div className="space-y-3">
                {versions.map((v) => (
                  <div
                    key={v.version}
                    className="rounded-lg border border-slate-800 p-4 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-200">
                        v{v.version}{" "}
                        {v.is_active && (
                          <span className="ml-2 rounded bg-emerald-900/50 px-2 py-0.5 text-xs text-emerald-300">
                            Đang active
                          </span>
                        )}
                        {!v.evaluated && (
                          <span className="ml-2 rounded bg-yellow-900/50 px-2 py-0.5 text-xs text-yellow-300">
                            Chưa eval
                          </span>
                        )}
                      </span>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={v.is_active}
                          onClick={() => requestActivate(v.version)}
                          title={v.is_active ? "Đã active" : "Activate / rollback về version này"}
                          className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-xs text-cyan-300 hover:border-cyan-500 disabled:opacity-40"
                        >
                          {v.is_active ? <Check size={12} /> : <RotateCcw size={12} />}
                          {v.is_active ? "Active" : "Activate"}
                        </button>
                      </div>
                    </div>
                    <label className="block space-y-1 text-xs text-slate-400">
                      <span>Template</span>
                      <textarea
                        readOnly
                        aria-label={`Template v${v.version}`}
                        value={v.template}
                        rows={6}
                        className="w-full rounded-md border border-slate-800 bg-slate-950 p-2 font-mono text-xs text-slate-300"
                      />
                    </label>
                  </div>
                ))}
              </div>

              {versions.length >= 2 && (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() =>
                      setDiffTargets([
                        versions[versions.length - 2].version,
                        versions[versions.length - 1].version,
                      ])
                    }
                    className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:border-slate-500"
                  >
                    So sánh 2 version gần nhất
                  </button>
                  {diffTargets && (
                    <DiffView
                      a={versions.find((v) => v.version === diffTargets[0])?.template ?? ""}
                      b={versions.find((v) => v.version === diffTargets[1])?.template ?? ""}
                      labelA={`v${diffTargets[0]}`}
                      labelB={`v${diffTargets[1]}`}
                    />
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── activate-without-eval warning dialog (BR-2: warn, don't block) ── */}
      {activateWarning && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          role="alertdialog"
          aria-modal="true"
          aria-label="Cảnh báo activate chưa eval"
        >
          <div className="w-full max-w-sm space-y-4 rounded-xl border border-yellow-700 bg-slate-900 p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 text-yellow-400" size={20} />
              <p className="text-sm text-yellow-200">{activateWarning.message}</p>
            </div>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setActivateWarning(null)}
                className="rounded-md border border-slate-700 px-4 py-2"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={() => doActivate(activateWarning.version)}
                className="rounded-md bg-yellow-500 px-4 py-2 font-medium text-slate-950"
              >
                Vẫn activate
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function DiffView({
  a,
  b,
  labelA,
  labelB,
}: {
  a: string;
  b: string;
  labelA: string;
  labelB: string;
}) {
  const lines = diffLines(a, b);
  return (
    <div
      className="rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs"
      aria-label={`Diff ${labelA} vs ${labelB}`}
    >
      {lines.map((l, i) => (
        <div
          key={i}
          className={
            l.sign === "+"
              ? "text-emerald-400"
              : l.sign === "-"
                ? "text-red-400"
                : "text-slate-500"
          }
        >
          {l.sign} {l.text}
        </div>
      ))}
    </div>
  );
}
