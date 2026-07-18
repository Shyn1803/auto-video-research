/**
 * history/page.tsx — task 5-9 "History tổng" secondary route.
 *
 * Locked decision (task file "Decisions already locked"): keep as a
 * secondary, low-traffic audit route — plain table of every version across
 * every step, no polished UI investment for v1.
 */

"use client";

import { useEffect, useState } from "react";
import { useWorkspace, STATION_VERSIONING_STEPS } from "@/lib/workspace-context";
import { listVersions, type VersionOut } from "@/lib/api/versions";

const ALL_STEPS = STATION_VERSIONING_STEPS.flat();

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function HistoryPage() {
  const { state } = useWorkspace();
  const [rows, setRows] = useState<VersionOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!state.projectId) return;
    setLoading(true);
    Promise.all(
      ALL_STEPS.map((step) =>
        listVersions(state.projectId, step)
          .then((res) => res.versions)
          .catch(() => [] as VersionOut[]),
      ),
    )
      .then((lists) => {
        if (cancelled) return;
        const all = lists.flat().sort((a, b) => b.created_at.localeCompare(a.created_at));
        setRows(all);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [state.projectId]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Lịch sử tất cả phiên bản</h2>
      <p className="text-sm text-muted-foreground">
        Bảng audit toàn bộ version của mọi bước — ít dùng, ưu tiên giá trị tra cứu, không đầu tư
        UI chi tiết ở v1.
      </p>

      {loading && <p className="text-sm text-muted-foreground">Đang tải…</p>}

      {!loading && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">Chưa có phiên bản nào.</p>
      )}

      {!loading && rows.length > 0 && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="py-2 pr-4">Bước</th>
              <th className="py-2 pr-4">Phiên bản</th>
              <th className="py-2 pr-4">Trạng thái</th>
              <th className="py-2 pr-4">Người tạo</th>
              <th className="py-2 pr-4">Thời gian</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => (
              <tr key={v.id} className="border-b border-border/60">
                <td className="py-2 pr-4">{v.step}</td>
                <td className="py-2 pr-4">v{v.version}</td>
                <td className="py-2 pr-4">{v.stale ? "Lỗi thời" : "Hiện hành/hợp lệ"}</td>
                <td className="py-2 pr-4">{v.created_by}</td>
                <td className="py-2 pr-4">{formatTimestamp(v.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
