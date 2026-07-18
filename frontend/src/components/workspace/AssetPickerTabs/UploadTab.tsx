/**
 * UploadTab — file upload with client-side validation + BR-2 dedupe notice.
 *
 * Locked decision (task 5-3 file): 10MB max, jpg/png/webp only. Client-side
 * validation is a UX nicety, not the security boundary — the backend
 * (AssetService.upload) re-validates identically and is authoritative.
 */

"use client";

import { useCallback, useState } from "react";
import { uploadAsset } from "@/lib/api/assets";

const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_BYTES = 10 * 1024 * 1024;

export interface UploadTabProps {
  onUploaded: (assetId: string) => void;
}

type UploadStatus = "idle" | "uploading" | "error";

export function UploadTab({ onUploaded }: UploadTabProps) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [reusedNotice, setReusedNotice] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setReusedNotice(null);

      if (!ALLOWED_TYPES.has(file.type)) {
        setError("Chỉ nhận ảnh JPG, PNG hoặc WEBP.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setError("Ảnh vượt quá 10MB.");
        return;
      }

      setStatus("uploading");
      try {
        const asset = await uploadAsset(file);
        if (asset.reused) {
          setReusedNotice("Ảnh này đã có trong hệ thống — dùng lại ảnh cũ.");
        }
        onUploaded(asset.id);
      } catch {
        setError("Tải ảnh thất bại. Thử lại sau.");
      } finally {
        setStatus("idle");
      }
    },
    [onUploaded],
  );

  return (
    <div className="space-y-3">
      <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border p-8 text-sm text-muted-foreground hover:border-primary">
        <span>Chọn ảnh từ máy tính (JPG/PNG/WEBP, tối đa 10MB)</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          disabled={status === "uploading"}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
            e.target.value = "";
          }}
        />
      </label>

      {status === "uploading" && (
        <p className="text-sm text-muted-foreground" role="status">
          Đang tải lên…
        </p>
      )}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      {reusedNotice && (
        <p className="text-sm text-muted-foreground" role="status">
          {reusedNotice}
        </p>
      )}
    </div>
  );
}
