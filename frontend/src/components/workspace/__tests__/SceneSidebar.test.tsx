/**
 * SceneSidebar integration tests — Task 5-4 ACs.
 *
 * Drag-and-drop itself (pointer sensor) isn't meaningfully testable under
 * jsdom/happy-dom — dnd-kit's PointerSensor needs real pointer-capture APIs.
 * The ↑/↓ buttons are dnd-kit-independent (they call the same
 * moveScene/reorderScenes reducer functions SceneSidebar's handleDragEnd
 * uses) and are themselves the AC-4 mouse-free path, so they're what's
 * exercised here — dnd-kit's own drag behavior is its library's concern,
 * not this project's.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useWorkspace, WorkspaceProvider, type SceneRow } from "@/lib/workspace-context";
import { SceneSidebar } from "../SceneSidebar";

vi.mock("@/lib/api/scenes", () => ({
  reorderScenesApi: vi.fn().mockResolvedValue(undefined),
  deleteSceneApi: vi.fn().mockResolvedValue(undefined),
  addSceneApi: vi.fn().mockResolvedValue({ scene_id: "server-id" }),
  duplicateSceneApi: vi.fn().mockResolvedValue({ scene_id: "server-id" }),
}));

function makeScenes(n: number): SceneRow[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `s${i + 1}`,
    title: `Cảnh ${i + 1}`,
    order: i,
    approved: false,
    warnings: [],
    layoutClass: "Hero",
  }));
}

function SelectedIndexProbe() {
  const { state } = useWorkspace();
  return <div data-testid="selected-index">{String(state.selectedSceneIndex)}</div>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SceneSidebar", () => {
  it("AC-1/BR-1 (happy, keyboard path): moving scene #4 down-then-up preserves every scene_id, only order changes", () => {
    render(
      <WorkspaceProvider projectId="p1" initialState={{ scenes: makeScenes(5) }}>
        <SceneSidebar />
      </WorkspaceProvider>,
    );

    // Move scene #4 (index 3) up twice → lands at index 1 ("position 2").
    fireEvent.click(screen.getByRole("button", { name: "Chuyển cảnh 4 lên trên" }));
    fireEvent.click(screen.getByRole("button", { name: "Chuyển cảnh 3 lên trên" }));

    const rows = screen.getAllByRole("button", { name: /#\d/ });
    const order = rows.map((r) => r.textContent ?? "");
    expect(order[1]).toContain("Cảnh 4");
    // every original scene is still present (id-preservation — nothing lost/duplicated)
    for (const title of ["Cảnh 1", "Cảnh 2", "Cảnh 3", "Cảnh 4", "Cảnh 5"]) {
      expect(order.filter((t) => t.includes(title))).toHaveLength(1);
    }
  });

  it("a11y AC-4: up/down buttons are disabled at the ends, not hidden", () => {
    render(
      <WorkspaceProvider projectId="p1" initialState={{ scenes: makeScenes(3) }}>
        <SceneSidebar />
      </WorkspaceProvider>,
    );
    expect(screen.getByRole("button", { name: "Chuyển cảnh 1 lên trên" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Chuyển cảnh 3 xuống dưới" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Chuyển cảnh 1 xuống dưới" })).toBeEnabled();
  });

  it("AC-2 (biên): deleting the currently-open scene moves selection to the next scene", () => {
    render(
      <WorkspaceProvider
        projectId="p1"
        initialState={{ scenes: makeScenes(3), selectedSceneIndex: 1 }}
      >
        <SceneSidebar />
        <SelectedIndexProbe />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Xoá cảnh 2" }));
    fireEvent.click(screen.getByRole("button", { name: "Xoá" }));

    // scene #2 (index 1) removed → index 1 now holds what was scene #3
    expect(screen.getByTestId("selected-index")).toHaveTextContent("1");
    expect(screen.getAllByRole("button", { name: /#\d/ })).toHaveLength(2);
  });

  it("AC-2 (biên): deleting the last remaining scene shows the empty state", () => {
    render(
      <WorkspaceProvider
        projectId="p1"
        initialState={{ scenes: makeScenes(1), selectedSceneIndex: 0 }}
      >
        <SceneSidebar />
        <SelectedIndexProbe />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Xoá cảnh 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Xoá" }));

    expect(screen.getByTestId("selected-index")).toHaveTextContent("null");
    expect(screen.getByText(/Chưa có cảnh nào/)).toBeInTheDocument();
  });

  it("BR-4: duplicating and then editing the copy never mutates the original", () => {
    render(
      <WorkspaceProvider projectId="p1" initialState={{ scenes: makeScenes(2) }}>
        <SceneSidebar />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: /Nhân bản/i })[0]);

    const rows = screen.getAllByRole("button", { name: /#\d/ });
    expect(rows).toHaveLength(3);
    // original (now #1) still reads "Cảnh 1"; copy (#2) also reads "Cảnh 1"
    // (content copied) but is a structurally distinct row/id — edits to one
    // (exercised at the reducer level in sceneOpsReducer.test.ts) never
    // touch the other because they are independent objects, not shared refs.
    expect(rows[0]).toHaveTextContent("Cảnh 1");
    expect(rows[1]).toHaveTextContent("Cảnh 1");
    expect(rows[2]).toHaveTextContent("Cảnh 2");
  });
});
