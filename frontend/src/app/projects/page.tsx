"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/interceptor";
import { Button } from "@/components/ui/button";
import { ProjectCard, type ProjectListItem } from "@/components/projects/ProjectCard";
import { CreateProjectModal } from "@/components/projects/CreateProjectModal";

interface ProjectGroup {
  key: string;
  label: string;
  order: number;
  projects: ProjectListItem[];
}

type ViewState = "default" | "loading" | "error" | "empty";
type ModeFilter = "all" | "interactive" | "daily_news";

/** Dashboard "Dự án của tôi" — grouped by lifecycle (BR-6), filter/search/paging,
 * first-run empty state, Create-project modal (task 1-3 Step 6). */
export default function ProjectsDashboardPage() {
  const router = useRouter();
  const [groups, setGroups] = useState<ProjectGroup[]>([]);
  const [view, setView] = useState<ViewState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<ModeFilter>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [everHadProjects, setEverHadProjects] = useState(true);

  const load = useCallback(async () => {
    setView("loading");
    try {
      const { data } = await api.get<ProjectGroup[]>("/projects/groups", {
        params: { mode, q: search || undefined },
      });
      setGroups(data);
      const total = data.reduce((acc, g) => acc + g.projects.length, 0);
      if (total === 0) {
        setView("empty");
      } else {
        setView("default");
        setEverHadProjects(true);
      }
    } catch (err: unknown) {
      setView("error");
      const e = err as { response?: { data?: { detail?: string } } };
      setErrorMsg(e?.response?.data?.detail ?? "Không tải được danh sách dự án");
    }
  }, [mode, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleArchive = useCallback(
    async (id: string) => {
      await api.post(`/projects/${id}/archive`);
      load();
    },
    [load]
  );

  const handleClone = useCallback(
    async (id: string) => {
      const { data } = await api.post<{ id: string }>(`/projects/${id}/clone`);
      load();
      router.push(`/projects/${data.id}`);
    },
    [load, router]
  );

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="m-0 text-xl font-semibold">Dự án</h2>
        <div className="flex gap-2">
          <label htmlFor="dashboard-search" className="sr-only">
            Tìm kiếm dự án
          </label>
          <input
            id="dashboard-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 Tìm kiếm…"
            className="w-[220px] rounded-md border border-border bg-background px-3 py-1.5 text-sm"
          />
          <Button onClick={() => setCreateOpen(true)}>+ Tạo dự án</Button>
        </div>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h3 className="m-0 text-base font-medium">Dự án của tôi</h3>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as ModeFilter)}
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          aria-label="Lọc theo chế độ"
        >
          <option value="all">Tất cả</option>
          <option value="interactive">Của tôi</option>
          <option value="daily_news">Tự động (Mode 1)</option>
        </select>
      </div>

      {view === "loading" && (
        <div aria-busy="true" className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[92px] animate-pulse rounded-lg border border-border bg-muted"
            />
          ))}
        </div>
      )}

      {view === "error" && (
        <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {errorMsg}{" "}
          <Button size="sm" variant="outline" onClick={load} className="ml-2">
            Thử lại
          </Button>
        </div>
      )}

      {view === "empty" && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-muted-foreground">
            {everHadProjects
              ? "Không tìm thấy dự án phù hợp"
              : "Tạo dự án đầu tiên — chỉ cần nhập chủ đề"}
          </p>
          <Button onClick={() => setCreateOpen(true)}>+ Tạo dự án</Button>
        </div>
      )}

      {view === "default" && (
        <div className="space-y-5">
          {groups.map((group) => (
            <div key={group.key}>
              <div className="mb-1.5 text-xs font-medium uppercase text-muted-foreground">
                {group.label}
              </div>
              <div className="space-y-2">
                {group.projects.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={p}
                    onArchive={handleArchive}
                    onClone={handleClone}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateProjectModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          setCreateOpen(false);
          router.push(`/projects/${id}`);
        }}
      />
    </div>
  );
}
