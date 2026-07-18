/**
 * LayoutDryRunDialog tests — task 5-2 Step 4 (AC-2 biên/BR-1).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { LayoutDryRunDialog } from "../LayoutDryRunDialog";
import { checkLayoutChange } from "@/lib/scene/layout-constraints";

const THREE_TEXTS = [
  { id: "t1", content: "Tiêu đề" },
  { id: "t2", content: "Nội dung chính" },
  { id: "t3", content: "Chú thích thêm" },
];

describe("checkLayoutChange (pure) — AC-2", () => {
  it("MediaText (3 texts) -> MediaFull (max 2) drops the 3rd text", () => {
    const result = checkLayoutChange(THREE_TEXTS, 1, "MediaFull");
    expect(result.ok).toBe(false);
    expect(result.droppedTextIds).toEqual(["t3"]);
  });

  it("no violation when target layout has room for all elements", () => {
    const result = checkLayoutChange(THREE_TEXTS, 1, "MediaText");
    expect(result.ok).toBe(true);
    expect(result.droppedTextIds).toEqual([]);
  });
});

describe("LayoutDryRunDialog", () => {
  it("AC-2: names the exact dropped element ('t3') on a violating layout change", () => {
    render(
      <LayoutDryRunDialog
        open
        fromLayout="MediaText"
        toLayout="MediaFull"
        texts={THREE_TEXTS}
        imagesCount={1}
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("chữ 't3' sẽ bị bỏ");
    expect(dialog).not.toHaveTextContent("t1' sẽ bị bỏ");
    expect(dialog).not.toHaveTextContent("t2' sẽ bị bỏ");
  });

  it("renders nothing when the target layout has no violation", () => {
    render(
      <LayoutDryRunDialog
        open
        fromLayout="MediaText"
        toLayout="MediaText"
        texts={THREE_TEXTS}
        imagesCount={1}
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("renders nothing when closed", () => {
    render(
      <LayoutDryRunDialog
        open={false}
        fromLayout="MediaText"
        toLayout="MediaFull"
        texts={THREE_TEXTS}
        imagesCount={1}
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("cancel invokes onCancel and confirm invokes onConfirm", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <LayoutDryRunDialog
        open
        fromLayout="MediaText"
        toLayout="MediaFull"
        texts={THREE_TEXTS}
        imagesCount={1}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />,
    );
    fireEvent.click(screen.getByText("Hủy"));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("Vẫn đổi"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  /** BR-1: "huỷ = nguyên trạng" — a realistic caller wiring: opening the
   * dialog must not itself commit the new layout; only explicit confirm does. */
  function LayoutPicker() {
    const [layout, setLayout] = useState("MediaText");
    const [pendingLayout, setPendingLayout] = useState<string | null>(null);

    return (
      <div>
        <span data-testid="current-layout">{layout}</span>
        <button
          type="button"
          onClick={() => {
            const result = checkLayoutChange(THREE_TEXTS, 1, "MediaFull");
            if (result.ok) {
              setLayout("MediaFull");
            } else {
              setPendingLayout("MediaFull");
            }
          }}
        >
          Đổi sang MediaFull
        </button>
        <LayoutDryRunDialog
          open={pendingLayout !== null}
          fromLayout={layout}
          toLayout={pendingLayout ?? ""}
          texts={THREE_TEXTS}
          imagesCount={1}
          onCancel={() => setPendingLayout(null)}
          onConfirm={() => {
            if (pendingLayout) setLayout(pendingLayout);
            setPendingLayout(null);
          }}
        />
      </div>
    );
  }

  it("BR-1: cancel leaves the scene's layout exactly as it was before the attempted change", () => {
    render(<LayoutPicker />);
    expect(screen.getByTestId("current-layout")).toHaveTextContent("MediaText");

    fireEvent.click(screen.getByText("Đổi sang MediaFull"));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("chữ 't3' sẽ bị bỏ");

    fireEvent.click(screen.getByText("Hủy"));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(screen.getByTestId("current-layout")).toHaveTextContent("MediaText");
  });

  it("BR-1: confirm commits the new layout after the warning", () => {
    render(<LayoutPicker />);
    fireEvent.click(screen.getByText("Đổi sang MediaFull"));
    fireEvent.click(screen.getByText("Vẫn đổi"));
    expect(screen.getByTestId("current-layout")).toHaveTextContent("MediaFull");
  });
});
