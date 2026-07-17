"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api/interceptor";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Trash2, Plus, AlertTriangle } from "lucide-react";

type FormState = "default" | "loading" | "error";
type ViewState = "default" | "loading" | "error" | "empty";

interface ApiKeyRow {
  id: string;
  provider: string;
  label: string;
  key_masked: string;
  status: "active" | "exhausted" | "revoked";
  usage_count: number;
  last_used_at: string | null;
  exhausted_until: string | null;
  created_at: string;
  updated_at: string;
}

interface ConsequenceResponse {
  warning: string | null;
  chain_providers: string[];
}

export function ApiKeysTable() {
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);
  const [view, setView] = useState<ViewState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  // create dialog
  const [openCreate, setOpenCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    provider: "gemini",
    label: "",
    key: "",
  });
  const [createState, setCreateState] = useState<FormState>("default");
  const [createErr, setCreateErr] = useState("");

  // delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{
    id: string;
    warning?: string;
  } | null>(null);
  const [deleteState, setDeleteState] = useState<FormState>("default");
  const [deleteErr, setDeleteErr] = useState("");

  const { accessToken } = useAuth();

  // ── load list ─────────────────────────────────────────────────────
  const loadKeys = useCallback(async () => {
    setView("loading");
    setErrorMsg("");
    try {
      const { data } = await api.get<ApiKeyRow[]>("/admin/api-keys");
      setKeys(data);
      setView(data.length === 0 ? "empty" : "default");
      // eslint-disable-next-line react-hooks/exhaustive-deps
    } catch {
      setView("error");
      setErrorMsg("Không tải được danh sách key");
    }
  }, []);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  // ── create key ────────────────────────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateErr("");
    setCreateState("loading");
    try {
      await api.post("/admin/api-keys", {
        provider: createForm.provider.trim().toLowerCase(),
        label: createForm.label.trim(),
        key: createForm.key,
      });
      setOpenCreate(false);
      setCreateForm({ provider: "gemini", label: "", key: "" });
      await loadKeys();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setCreateErr(
        e?.response?.data?.detail ?? "Lỗi thêm key",
      );
      setCreateState("error");
    } finally {
      setCreateState((s) => (s === "loading" ? "default" : s));
    }
  };

  // ── delete — two-step: check consequence, then confirm ─────────────
  const requestDelete = async (id: string) => {
    setDeleteErr("");
    setDeleteState("default");
    try {
      const { data } = await api.delete<ConsequenceResponse>(
        `/admin/api-keys/${id}`,
      );
      setDeleteConfirm({
        id,
        warning: data.warning ?? undefined,
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setDeleteErr(e?.response?.data?.detail ?? "Không thể kiểm tra key");
      setDeleteState("error");
    }
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    setDeleteErr("");
    setDeleteState("loading");
    try {
      await api.post(`/admin/api-keys/${deleteConfirm.id}/confirm-delete`);
      setDeleteConfirm(null);
      await loadKeys();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setDeleteErr(e?.response?.data?.detail ?? "Không thể xoá key");
      setDeleteState("error");
    } finally {
      setDeleteState((s) => (s === "loading" ? "default" : s));
    }
  };

  // ── render ────────────────────────────────────────────────────────
  return (
    <section className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-50">API Keys</h1>
          <p className="text-sm text-slate-400">
            Quản lý key nhà cung cấp — mã hoá Fernet, xoay vòng tự động.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpenCreate(true)}
          className="rounded-md bg-cyan-400 px-4 py-2 font-medium text-slate-950 hover:bg-cyan-300"
        >
          <span className="inline-flex items-center gap-1">
            <Plus size={16} /> Thêm key
          </span>
        </button>
      </header>

      {/* ── table ───────────────────────────────────────────────── */}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm" caption="Danh sách API keys">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Label</th>
              <th className="px-4 py-3">Key</th>
              <th className="px-4 py-3">Trạng thái</th>
              <th className="px-4 py-3 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {view === "loading" && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-slate-500">
                  Đang tải…
                </td>
              </tr>
            )}
            {view === "error" && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-red-400">
                  {errorMsg}
                </td>
              </tr>
            )}
            {view === "empty" && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-slate-500">
                  Chưa có API key nào.{" "}
                  <a
                    href="/settings"
                    target="_blank"
                    rel="noopener"
                    className="text-cyan-400 underline"
                  >
                    Xem hướng dẫn cấu hình
                  </a>
                  .
                </td>
              </tr>
            )}
            {keys.map((k) => (
              <tr
                key={k.id}
                className="border-b border-slate-800/60 hover:bg-slate-900/40"
              >
                <td className="px-4 py-3 text-slate-200">{k.provider}</td>
                <td className="px-4 py-3">{k.label}</td>
                <td className="px-4 py-3 font-mono text-slate-400">
                  {k.key_masked}
                </td>
                <td className="px-4 py-3">
                  {statusBadge(k.status)}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => requestDelete(k.id)}
                    title="Xoá key"
                    disabled={deleteState === "loading"}
                    className="rounded-md border border-slate-700 px-2 py-1 text-sm text-red-400 hover:border-red-500 disabled:opacity-40"
                  >
                    <span className="inline-flex items-center gap-1">
                      <Trash2 size={14} /> Xoá
                    </span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── create dialog ───────────────────────────────────────── */}
      {openCreate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          role="dialog"
          aria-modal="true"
          aria-label="Thêm API key"
        >
          <form
            onSubmit={handleCreate}
            className="w-full max-w-md space-y-4 rounded-xl border border-slate-700 bg-slate-900 p-6"
          >
            <h2 className="text-lg font-semibold">Thêm API key</h2>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-300">Provider</span>
              <select
                aria-label="Provider"
                value={createForm.provider}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, provider: e.target.value }))
                }
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
              >
                {[
                  "gemini",
                  "groq",
                  "openrouter",
                  "tavily",
                  "brave",
                  "fpt",
                  "elevenlabs",
                ].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-300">Label (tên hiển thị)</span>
              <input
                type="text"
                aria-label="Label"
                required
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
                value={createForm.label}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, label: e.target.value }))
                }
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-300">API Key</span>
              <input
                type="password"
                aria-label="API Key"
                required
                minLength={4}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
                value={createForm.key}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, key: e.target.value }))
                }
              />
            </label>
            {createErr && (
              <p className="text-sm text-red-400" role="alert">
                {createErr}
              </p>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setOpenCreate(false)}
                className="rounded-md border border-slate-700 px-4 py-2"
              >
                Hủy
              </button>
              <button
                type="submit"
                disabled={createState === "loading"}
                className="rounded-md bg-cyan-400 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
              >
                {createState === "loading" ? "Đang lưu…" : "Lưu key"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── delete consequence dialog ─────────────────────────────── */}
      {deleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          role="alertdialog"
          aria-modal="true"
          aria-label="Xác nhận xoá key"
        >
          <div className="w-full max-w-sm rounded-xl border border-yellow-700 bg-slate-900 p-6 space-y-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 text-yellow-400" size={20} />
              <div>
                <h3 className="text-lg font-semibold">Xác nhận xoá key</h3>
                {deleteConfirm.warning ? (
                  <p className="mt-1 text-sm text-yellow-200">
                    {deleteConfirm.warning}
                  </p>
                ) : (
                  <p className="mt-1 text-sm text-slate-300">
                    Bạn có chắc muốn xoá key này? Hành động không thể hoàn
                    tác.
                  </p>
                )}
              </div>
            </div>
            {deleteErr && (
              <p className="text-sm text-red-400" role="alert">
                {deleteErr}
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteConfirm(null)}
                className="rounded-md border border-slate-700 px-4 py-2"
              >
                Giữ lại
              </button>
              <button
                type="button"
                disabled={deleteState === "loading"}
                onClick={confirmDelete}
                className="rounded-md bg-red-500 px-4 py-2 font-medium text-white disabled:opacity-50"
              >
                {deleteState === "loading" ? "Đang xoá…" : "Vẫn xoá"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function statusBadge(status: ApiKeyRow["status"]) {
  const cls: Record<string, string> = {
    active: "text-emerald-400",
    exhausted: "text-yellow-400",
    revoked: "text-red-400",
  };
  const label: Record<string, string> = {
    active: "Active",
    exhausted: "Hết quota",
    revoked: "Đã thu hồi",
  };
  return <span className={cls[status]}>{label[status] ?? status}</span>;
}
