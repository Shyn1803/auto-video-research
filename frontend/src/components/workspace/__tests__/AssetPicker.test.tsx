/**
 * AssetPicker modal shell tests — Task 5-3 Step 2/6.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AssetPicker } from "../AssetPicker";
import * as assetsApi from "@/lib/api/assets";

vi.mock("@/lib/api/assets", () => ({
  fetchStockStatus: vi.fn(),
  searchStock: vi.fn(),
  fetchStockAsset: vi.fn(),
  uploadAsset: vi.fn(),
}));

const mockedApi = vi.mocked(assetsApi);

beforeEach(() => {
  vi.resetAllMocks();
  mockedApi.fetchStockStatus.mockResolvedValue({ active: true, providers: ["pexels"] });
});

describe("AssetPicker", () => {
  it("renders nothing when closed", () => {
    render(
      <AssetPicker open={false} onClose={() => {}} onAssetSelected={() => {}} />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens with 3 tabs and defaults to Asset dự án when no prefill query", () => {
    render(<AssetPicker open onClose={() => {}} onAssetSelected={() => {}} />);
    const dialog = screen.getByRole("dialog", { name: "Đổi ảnh" });
    expect(dialog).toBeInTheDocument();

    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["Asset dự án", "Tải lên", "Tìm stock"]);
    expect(screen.getByRole("tab", { name: "Asset dự án" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("defaults to the Tìm stock tab when a prefill query is provided", async () => {
    render(
      <AssetPicker
        open
        onClose={() => {}}
        onAssetSelected={() => {}}
        initialStockQuery="GPU datacenter"
      />,
    );
    expect(screen.getByRole("tab", { name: "Tìm stock" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await waitFor(() => expect(mockedApi.fetchStockStatus).toHaveBeenCalled());
  });

  it("switches tabs on click", () => {
    render(<AssetPicker open onClose={() => {}} onAssetSelected={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: "Tải lên" }));
    expect(screen.getByRole("tab", { name: "Tải lên" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/Chọn ảnh từ máy tính/)).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(<AssetPicker open onClose={onClose} onAssetSelected={() => {}} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes when clicking the backdrop", () => {
    const onClose = vi.fn();
    const { container } = render(
      <AssetPicker open onClose={onClose} onAssetSelected={() => {}} />,
    );
    const backdrop = container.firstElementChild as HTMLElement;
    fireEvent.mouseDown(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes via the visible close button", () => {
    const onClose = vi.fn();
    render(<AssetPicker open onClose={onClose} onAssetSelected={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
