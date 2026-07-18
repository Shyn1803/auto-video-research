/**
 * StockSearchTab tests — Task 5-3 Step 3/4.
 *
 * AC1 (happy): search -> results show license + source BEFORE selection (BR-1).
 * AC3 (BR-3): 0 key -> tab disabled, role-appropriate message (admin vs creator).
 * AC5 (BR-4): selecting a result shows "đang lấy ảnh…" while fetch-stock resolves,
 *             then calls onSelected with the internal asset_id (never a raw url).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { StockSearchTab } from "../StockSearchTab";
import * as assetsApi from "@/lib/api/assets";

vi.mock("@/lib/api/assets", () => ({
  fetchStockStatus: vi.fn(),
  searchStock: vi.fn(),
  fetchStockAsset: vi.fn(),
}));

const mockedApi = vi.mocked(assetsApi);

beforeEach(() => {
  vi.resetAllMocks();
});

describe("StockSearchTab — BR-3 gating", () => {
  it("disables the tab with an admin link when no provider key is active", async () => {
    mockedApi.fetchStockStatus.mockResolvedValue({ active: false, providers: [] });
    render(<StockSearchTab userRole="admin" onSelected={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText(/Chưa có nguồn ảnh stock nào hoạt động/)).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: /Quản trị/ })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("disables the tab with a 'ask admin' message for a creator", async () => {
    mockedApi.fetchStockStatus.mockResolvedValue({ active: false, providers: [] });
    render(<StockSearchTab userRole="creator" onSelected={() => {}} />);

    await waitFor(() => expect(screen.getByText(/nhờ admin thêm key/i)).toBeInTheDocument());
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("enables the search box when at least one provider is active", async () => {
    mockedApi.fetchStockStatus.mockResolvedValue({ active: true, providers: ["pexels"] });
    render(<StockSearchTab userRole="creator" onSelected={() => {}} />);

    await waitFor(() => expect(screen.getByRole("textbox")).toBeInTheDocument());
  });
});

describe("StockSearchTab — BR-1: license + source before selection", () => {
  it("shows license and attribution badge on every result before any click", async () => {
    mockedApi.fetchStockStatus.mockResolvedValue({ active: true, providers: ["pexels"] });
    mockedApi.searchStock.mockResolvedValue([
      {
        provider: "pexels",
        url: "https://images.pexels.com/photos/1/gpu.jpg",
        thumb_url: "https://images.pexels.com/photos/1/gpu-thumb.jpg",
        attribution: "Jane Doe",
        attribution_url: "https://pexels.com/@jane",
        license: "Pexels License",
        width: "1920",
        height: "1080",
      },
    ]);

    render(<StockSearchTab userRole="creator" onSelected={() => {}} />);
    await waitFor(() => expect(screen.getByRole("textbox")).toBeInTheDocument());

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "GPU datacenter" } });
    fireEvent.click(screen.getByRole("button", { name: "Tìm" }));

    await waitFor(() => expect(screen.getByRole("grid")).toBeInTheDocument());
    expect(screen.getByText("Pexels License")).toBeInTheDocument();
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    // license/attribution rendered as part of the same result card, before any selection happened
    expect(mockedApi.fetchStockAsset).not.toHaveBeenCalled();
  });
});

describe("StockSearchTab — BR-4: server-side fetch on select", () => {
  it("shows 'đang lấy ảnh…' while fetching, then resolves to an internal asset_id", async () => {
    mockedApi.fetchStockStatus.mockResolvedValue({ active: true, providers: ["pexels"] });
    mockedApi.searchStock.mockResolvedValue([
      {
        provider: "pexels",
        url: "https://images.pexels.com/photos/1/gpu.jpg",
        thumb_url: "https://images.pexels.com/photos/1/gpu-thumb.jpg",
        attribution: "Jane Doe",
        attribution_url: "",
        license: "Pexels License",
        width: "1920",
        height: "1080",
      },
    ]);
    let resolveFetch: (v: Awaited<ReturnType<typeof assetsApi.fetchStockAsset>>) => void = () => {};
    mockedApi.fetchStockAsset.mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );

    const onSelected = vi.fn();
    render(<StockSearchTab initialQuery="GPU datacenter" userRole="creator" onSelected={onSelected} />);

    await waitFor(() => expect(screen.getByRole("grid")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("gridcell"));

    await waitFor(() => expect(screen.getByText("Đang lấy ảnh…")).toBeInTheDocument());
    expect(mockedApi.fetchStockAsset).toHaveBeenCalledWith(
      expect.objectContaining({
        url: "https://images.pexels.com/photos/1/gpu.jpg",
        provider: "pexels",
        license: "Pexels License",
      }),
    );

    resolveFetch({
      id: "asset-123",
      provider: "pexels",
      license: "Pexels License",
      attribution_required: true,
      attribution_text: "Jane Doe",
      storage_path: "assets/abc.jpg",
      content_hash: "abc",
      reused: false,
    });

    await waitFor(() => expect(onSelected).toHaveBeenCalledWith("asset-123"));
  });
});
