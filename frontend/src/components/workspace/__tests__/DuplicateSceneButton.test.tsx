/**
 * DuplicateSceneButton tests — Task 5-4 Step 4 (AC-3 / BR-4).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useWorkspace, WorkspaceProvider, type SceneRow } from "@/lib/workspace-context";
import { DuplicateSceneButton } from "../DuplicateSceneButton";

vi.mock("@/lib/api/scenes", () => ({
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

function SceneListProbe() {
  const { state } = useWorkspace();
  return (
    <ul>
      {state.scenes.map((s) => (
        <li key={s.id} data-id={s.id}>
          {s.title}
        </li>
      ))}
    </ul>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DuplicateSceneButton", () => {
  it("BR-4: inserts a copy right after the original with a brand-new id, same content", () => {
    render(
      <WorkspaceProvider projectId="p1" initialState={{ scenes: makeScenes(2) }}>
        <DuplicateSceneButton sceneId="s1" />
        <SceneListProbe />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Nhân bản/i }));

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveAttribute("data-id", "s1");
    expect(items[2]).toHaveAttribute("data-id", "s2");
    // the copy (middle item) has a new id, distinct from every existing one
    const copyId = items[1].getAttribute("data-id");
    expect(copyId).not.toBe("s1");
    expect(copyId).not.toBe("s2");
    expect(items[1]).toHaveTextContent("Cảnh 1"); // content copied from original
  });

  it("is a no-op when the given sceneId doesn't exist (defensive)", () => {
    render(
      <WorkspaceProvider projectId="p1" initialState={{ scenes: makeScenes(2) }}>
        <DuplicateSceneButton sceneId="does-not-exist" />
        <SceneListProbe />
      </WorkspaceProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Nhân bản/i }));
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });
});
