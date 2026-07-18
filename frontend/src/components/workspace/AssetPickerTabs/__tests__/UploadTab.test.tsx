/**
 * UploadTab tests — Task 5-3 Step 5 (BR-2 dedupe, locked-decision validation).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { UploadTab } from "../UploadTab";
import * as assetsApi from "@/lib/api/assets";

vi.mock("@/lib/api/assets", () => ({
  uploadAsset: vi.fn(),
}));

const mockedApi = vi.mocked(assetsApi);

beforeEach(() => {
  vi.resetAllMocks();
});

function makeFile(name: string, type: string, sizeBytes: number): File {
  const bytes = new Uint8Array(sizeBytes);
  return new File([bytes], name, { type });
}

describe("UploadTab", () => {
  it("rejects a file with a disallowed type client-side (no upload call)", async () => {
    render(<UploadTab onUploaded={() => {}} />);
    const input = screen.getByLabelText(/Chọn ảnh từ máy tính/) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [makeFile("a.gif", "image/gif", 100)] } });

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("JPG, PNG hoặc WEBP"));
    expect(mockedApi.uploadAsset).not.toHaveBeenCalled();
  });

  it("rejects a file over 10MB client-side (no upload call)", async () => {
    render(<UploadTab onUploaded={() => {}} />);
    const input = screen.getByLabelText(/Chọn ảnh từ máy tính/) as HTMLInputElement;

    const oversize = 10 * 1024 * 1024 + 1;
    fireEvent.change(input, {
      target: { files: [makeFile("big.png", "image/png", oversize)] },
    });

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("vượt quá 10MB"));
    expect(mockedApi.uploadAsset).not.toHaveBeenCalled();
  });

  it("accepts a valid file, uploads it, and calls onUploaded with the asset_id", async () => {
    mockedApi.uploadAsset.mockResolvedValue({
      id: "asset-1",
      provider: "user_upload",
      license: "user_upload",
      attribution_required: false,
      attribution_text: null,
      storage_path: "assets/x.png",
      content_hash: "x",
      reused: false,
    });
    const onUploaded = vi.fn();
    render(<UploadTab onUploaded={onUploaded} />);
    const input = screen.getByLabelText(/Chọn ảnh từ máy tính/) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [makeFile("ok.png", "image/png", 1024)] } });

    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith("asset-1"));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("BR-2: shows a reuse notice instead of implying a new record when the backend dedupes", async () => {
    mockedApi.uploadAsset.mockResolvedValue({
      id: "asset-existing",
      provider: "user_upload",
      license: "user_upload",
      attribution_required: false,
      attribution_text: null,
      storage_path: "assets/existing.png",
      content_hash: "existing-hash",
      reused: true,
    });
    const onUploaded = vi.fn();
    render(<UploadTab onUploaded={onUploaded} />);
    const input = screen.getByLabelText(/Chọn ảnh từ máy tính/) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [makeFile("dup.png", "image/png", 1024)] } });

    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith("asset-existing"));
    expect(screen.getByText(/đã có trong hệ thống/)).toBeInTheDocument();
  });
});
