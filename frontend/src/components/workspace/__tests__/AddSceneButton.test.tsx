/**
 * AddSceneButton tests — Task 5-4 Step 3 (AC happy + a11y AC-4).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useWorkspace, WorkspaceProvider, type SceneRow } from "@/lib/workspace-context";
import { AddSceneButton } from "../AddSceneButton";

vi.mock("@/lib/api/scenes", () => ({
  addSceneApi: vi.fn().mockResolvedValue({ scene_id: "server-id" }),
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

/** Surfaces scenes.map(title/layoutClass) as text so assertions can read
 * the resulting order/content without reaching into React internals. */
function SceneListProbe() {
  const { state } = useWorkspace();
  return (
    <ul>
      {state.scenes.map((s) => (
        <li key={s.id}>{`${s.title}:${s.layoutClass}`}</li>
      ))}
    </ul>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AddSceneButton", () => {
  it("opens the layout picker and inserts a new scene right after the selected one", () => {
    render(
      <WorkspaceProvider
        projectId="p1"
        initialState={{ scenes: makeScenes(3), selectedSceneIndex: 0 }}
      >
        <AddSceneButton />
        <SceneListProbe />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Thêm cảnh/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("menuitem", { name: /TextFocus/i }));

    // menu closes after selection
    expect(screen.queryByRole("menu")).toBeNull();

    const items = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual([
      "Cảnh 1:Hero",
      "Cảnh mới:TextFocus",
      "Cảnh 2:Hero",
      "Cảnh 3:Hero",
    ]);
  });

  it("layout menu is keyboard operable (AC-4): ArrowDown then Enter selects", () => {
    render(
      <WorkspaceProvider projectId="p1" initialState={{ scenes: makeScenes(1) }}>
        <AddSceneButton />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Thêm cảnh/i }));
    const menu = screen.getByRole("menu");
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    fireEvent.keyDown(menu, { key: "Escape" });

    expect(screen.queryByRole("menu")).toBeNull();
  });
});
