/**
 * VersionSwitcher tests — task 5-9 Step 1 AC.
 *
 * Co-located under src/components/workspace/__tests__ (vitest.config.ts's
 * `include` only picks up src/**\/*.test.{ts,tsx} — see PipelineStepper's
 * own test-file comment for why frontend/tests/unit/... isn't used).
 *
 * Mocks `@/lib/api/versions` — no live network calls in the unit suite
 * (rules/testing.md).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import VersionSwitcher from "../VersionSwitcher";
import { WorkspaceProvider, type WorkspaceState } from "@/lib/workspace-context";

const { listVersionsMock, getCurrentVersionMock } = vi.hoisted(() => ({
  listVersionsMock: vi.fn(),
  getCurrentVersionMock: vi.fn(),
}));

vi.mock("@/lib/api/versions", () => ({
  listVersions: listVersionsMock,
  getCurrentVersion: getCurrentVersionMock,
  getVersionDetail: vi.fn(),
  compareVersions: vi.fn(),
  restoreVersion: vi.fn(),
}));

function renderSwitcher(initialState?: Partial<WorkspaceState>) {
  return render(
    <WorkspaceProvider projectId="p1" initialState={{ projectId: "p1", ...initialState }}>
      <VersionSwitcher step="scene_set" />
    </WorkspaceProvider>,
  );
}

const THREE_VERSIONS = [
  { id: "v3", version: 3, step: "scene_set", stale: false, parent_version: 2, created_by: "AI", created_at: "2026-07-18T10:00:00Z" },
  { id: "v2", version: 2, step: "scene_set", stale: true, parent_version: 1, created_by: "user1", created_at: "2026-07-17T10:00:00Z" },
  { id: "v1", version: 1, step: "scene_set", stale: false, parent_version: null, created_by: "AI", created_at: "2026-07-16T10:00:00Z" },
];

describe("VersionSwitcher", () => {
  beforeEach(() => {
    listVersionsMock.mockReset();
    getCurrentVersionMock.mockReset();
  });

  it("renders the version list with timestamp, author, and stale badge+tooltip", async () => {
    listVersionsMock.mockResolvedValue({ versions: THREE_VERSIONS });
    getCurrentVersionMock.mockResolvedValue({ current: THREE_VERSIONS[0], all_stale: false });

    renderSwitcher();
    fireEvent.click(screen.getByRole("button", { name: /Phiên bản/ }));

    await waitFor(() => expect(screen.getByText("v3")).toBeInTheDocument());
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText(/user1/)).toBeInTheDocument();

    const staleBadges = screen.getAllByText("lỗi thời");
    expect(staleBadges.length).toBeGreaterThan(0);
    const staleBadge = staleBadges.find((el) => el.getAttribute("title"));
    expect(staleBadge).toBeDefined();
    expect(staleBadge!.getAttribute("title")).toMatch(/lỗi thời/);
  });

  it("AC-4 (empty): a step with only 1 version shows an explanatory message, not a broken dropdown", async () => {
    listVersionsMock.mockResolvedValue({ versions: [THREE_VERSIONS[0]] });
    getCurrentVersionMock.mockResolvedValue({ current: THREE_VERSIONS[0], all_stale: false });

    renderSwitcher();
    fireEvent.click(screen.getByRole("button", { name: /Phiên bản/ }));

    await waitFor(() =>
      expect(screen.getByText(/Chỉ có 1 phiên bản/)).toBeInTheDocument(),
    );
  });

  it("shows an all-stale banner when every version of the step is stale (BR-4)", async () => {
    listVersionsMock.mockResolvedValue({ versions: THREE_VERSIONS });
    getCurrentVersionMock.mockResolvedValue({ current: THREE_VERSIONS[0], all_stale: true });

    renderSwitcher();
    fireEvent.click(screen.getByRole("button", { name: /Phiên bản/ }));
    await waitFor(() =>
      expect(screen.getByTitle("Mọi phiên bản của bước này đều đã lỗi thời")).toBeInTheDocument(),
    );
  });
});
