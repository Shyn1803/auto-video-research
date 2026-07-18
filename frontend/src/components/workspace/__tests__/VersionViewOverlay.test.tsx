/**
 * VersionViewOverlay tests — task 5-9 Step 2 AC.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import VersionViewOverlay from "../VersionViewOverlay";

const { getVersionDetailMock } = vi.hoisted(() => ({
  getVersionDetailMock: vi.fn(),
}));

vi.mock("@/lib/api/versions", () => ({
  getVersionDetail: getVersionDetailMock,
}));

describe("VersionViewOverlay", () => {
  beforeEach(() => {
    getVersionDetailMock.mockReset();
  });

  it("renders the past version's content readonly, without an editable form", async () => {
    getVersionDetailMock.mockResolvedValue({
      id: "v2",
      version: 2,
      step: "scene_set",
      stale: false,
      parent_version: 1,
      created_by: "AI",
      created_at: "2026-07-17T10:00:00Z",
      content: { scenes: [{ scene_id: "s1", title: "Cảnh 1" }] },
    });

    const onClose = vi.fn();
    render(<VersionViewOverlay projectId="p1" step="scene_set" version={2} onClose={onClose} />);

    await waitFor(() => expect(screen.getByText(/Cảnh 1/)).toBeInTheDocument());

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    // Readonly: no <input>/<textarea> anywhere in the overlay.
    expect(dialog.querySelector("input, textarea")).toBeNull();
  });

  it("calls onClose when the close button is clicked (current editable state is untouched underneath)", async () => {
    getVersionDetailMock.mockResolvedValue({
      id: "v2",
      version: 2,
      step: "scene_set",
      stale: false,
      parent_version: 1,
      created_by: "AI",
      created_at: "2026-07-17T10:00:00Z",
      content: { text: "nội dung cũ" },
    });
    const onClose = vi.fn();
    render(<VersionViewOverlay projectId="p1" step="scene_set" version={2} onClose={onClose} />);

    await waitFor(() => expect(screen.getByText(/nội dung cũ/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
