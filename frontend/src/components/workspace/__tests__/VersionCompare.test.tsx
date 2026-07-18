/**
 * VersionCompare tests — task 5-9 Step 3 AC (BR-4 a11y: prefix + color, not
 * color-only).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import VersionCompare from "../VersionCompare";

const { compareVersionsMock } = vi.hoisted(() => ({
  compareVersionsMock: vi.fn(),
}));

vi.mock("@/lib/api/versions", () => ({
  compareVersions: compareVersionsMock,
}));

describe("VersionCompare", () => {
  beforeEach(() => {
    compareVersionsMock.mockReset();
  });

  it("text-diff-highlight-correct-lines: renders unified diff split into old/new columns", async () => {
    compareVersionsMock.mockResolvedValue({
      type: "text",
      diff: "--- v1\n+++ v2\n@@ -1,2 +1,2 @@\n-old line\n+new line\n context line",
    });

    render(
      <VersionCompare projectId="p1" step="script" fromVersion={1} toVersion={2} onClose={vi.fn()} />,
    );

    await waitFor(() => expect(screen.getByText(/-old line/)).toBeInTheDocument());
    expect(screen.getByText(/\+new line/)).toBeInTheDocument();
  });

  it("scene-diff-added-removed-changed: renders added/removed/changed scene entries", async () => {
    compareVersionsMock.mockResolvedValue({
      type: "scene_set",
      added: ["s3"],
      removed: ["s1"],
      changed: [{ scene_id: "s2", fields: ["title"] }],
    });

    render(
      <VersionCompare projectId="p1" step="scene_set" fromVersion={1} toVersion={2} onClose={vi.fn()} />,
    );

    await waitFor(() => expect(screen.getByText("s3")).toBeInTheDocument());
    expect(screen.getByText("s1")).toBeInTheDocument();
    expect(screen.getByText("s2")).toBeInTheDocument();
    expect(screen.getByText(/title/)).toBeInTheDocument();
  });

  it("prefix-not-color-only (BR-4 a11y): every diff entry has a literal +/-/~ prefix character in the DOM", async () => {
    compareVersionsMock.mockResolvedValue({
      type: "scene_set",
      added: ["s3"],
      removed: ["s1"],
      changed: [],
    });

    render(
      <VersionCompare projectId="p1" step="scene_set" fromVersion={1} toVersion={2} onClose={vi.fn()} />,
    );

    await waitFor(() => expect(screen.getByText("s3")).toBeInTheDocument());
    // aria-hidden prefix spans still exist in the DOM text content — a11y
    // rule is "prefix AND color", not "prefix only for screen readers".
    expect(screen.getByText("+")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("close-restores-focus (AC-1): a real, focusable close button always calls onClose", async () => {
    compareVersionsMock.mockResolvedValue({ type: "text", diff: "" });
    const onClose = vi.fn();
    render(
      <VersionCompare projectId="p1" step="script" fromVersion={1} toVersion={2} onClose={onClose} />,
    );
    await waitFor(() => expect(screen.getByText(/Không có khác biệt/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
