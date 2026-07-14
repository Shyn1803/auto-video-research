/**
 * scenes/page.tsx — Phân cảnh screen (Step 3 + BR-5).
 *
 * 3-column layout per wireframe:
 *   - SceneSidebar    (col 1, width 176px)
 *   - SceneFormPanel  (col 2, flex-1)
 *   - ScenePlayerPanel (col 3, flex-1)
 *
 * Header: "Đã duyệt x/y" computed from `state.approvedCount` (BR-5, realtime).
 * Bottom: ApproveBar (design-system §3.3, sticky bottom-right).
 *
 * This page also owns:
 *  - BR-1: clicking a done station triggers readonly + "Edit from here"
 *    (handled by the store + PipelineStepper; form banner rendered by SceneFormPanel)
 *  - BR-5: the approved-count header wires live off `useWorkspace`
 */

"use client";

import { useMemo } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { SceneSidebar } from "@/components/workspace/SceneSidebar";
import { SceneFormPanel } from "@/components/workspace/SceneFormPanel";
import { ScenePlayerPanel } from "@/components/workspace/ScenePlayerPanel";
import { ApproveBar } from "@/components/workspace/ApproveBar";
import { StatusBadge } from "@/components/ui/status-badge";

const FIXTURE_SCENES = [
  {
    id: "1", title: "Tiêu đề", order: 0, approved: true,  warnings: [],
    layoutClass: "Hero",
  },
  {
    id: "2", title: "Ảnh+chữ", order: 1, approved: false, warnings: ["thiếu ảnh minh hoạ"],
    layoutClass: "MediaText",
  },
  {
    id: "3", title: "Biểu đồ", order: 2, approved: true,  warnings: [],
    layoutClass: "Chart",
  },
  {
    id: "4", title: "Số lớn",   order: 3, approved: true,  warnings: [],
    layoutClass: "BigNumber",
  },
  {
    id: "5", title: "Bảng VS",  order: 4, approved: false, warnings: ["chưa đủ 2 nguồn"],
    layoutClass: "VersusTable",
  },
];

// Minimal ScenePlayer stubs — story 2-2 wires the real composition
const ComponentStub = () => null;
const DUMMY_SCENE = {
  duration_ms: 6000,
  format: "vertical_1080x1920" as const,
};

export default function ScenesPage() {
  const { state, dispatch } = useWorkspace();

  // In 5-1: bootstrap from local fixture — real GET/PUT wires in 5-2
  const scenes = useMemo(
    () =>
      state.scenes.length > 0
        ? state.scenes
        : FIXTURE_SCENES.map((f) => ({
            ...f,
            approved: f.approved,
            warnings: f.warnings,
          })),
    [state.scenes],
  );

  const approvedCount = scenes.filter((s) => s.approved).length;
  const allApproved = approvedCount === scenes.length;
  const doneWithWarning = approvedCount > 0 && !allApproved;

  return (
    <>
      {/* BR-5 header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Phân cảnh</h2>
          {doneWithWarning && (
            <span className="text-sm text-status-warn">
              ⚠ {scenes.filter((s) => s.warnings.length > 0).length} cảnh có cảnh báo
            </span>
          )}
        </div>
        <StatusBadge
          kind={allApproved ? "pass" : doneWithWarning ? "warn" : "run"}
          label={allApproved ? "Đủ" : doneWithWarning ? "Đang duyệt" : "Chờ duyệt"}
        />
      </div>

      <p className="text-sm text-muted-foreground">
        Đã duyệt {approvedCount}/{scenes.length} cảnh
        {!allApproved && " — duyệt đủ cảnh để sang Hoàn thiện"}
      </p>

      {/* 3-column Phân cảnh frame */}
      <div className="flex gap-4">
        <SceneSidebar />
        <SceneFormPanel />
        <ScenePlayerPanel component={ComponentStub} scene={DUMMY_SCENE} />
      </div>

      {/* ApproveBar — design-system §3.3 (sticky bottom-right) */}
      <ApproveBar
        approvedCount={approvedCount}
        totalScenes={scenes.length}
        primaryLabel="Sang Hoàn thiện ▸"
        secondaryLabel="↻ Tạo lại"
        disabledReason={
          !allApproved
            ? `Còn ${scenes.filter((s) => !s.approved).length} cảnh chưa duyệt`
            : undefined
        }
        onPrimaryAction={() => {
          dispatch({ type: "SET_CURRENT_STATION", index: 3 });
          dispatch({ type: "SET_STATION_STATES", states: ["done","done","done","current","locked"] });
          window.alert("→ Hoàn thiện (5-5 implements this screen)");
        }}
        onSecondaryAction={() => {
          console.log("[ScenesPage] Regen whole scene set");
        }}
      />
    </>
  );
}
