/**
 * Dev harness for AssetPicker (Task 5-3) — NOT part of the product nav.
 *
 * SceneFormPanel's real "Đổi ảnh…" trigger (docs/design/wireframe.html,
 * "Ảnh minh hoạ" section) is owned by task 5-2/5-4's in-progress work on
 * that file — wiring AssetPicker directly into it here would risk clobbering
 * concurrent edits. This route exists solely so the component can be
 * exercised end-to-end (real dev server + Playwright) per rules/testing.md
 * ("UI/frontend stories require exercising the feature in a real running
 * browser"), independent of that integration. Whoever wires the real
 * trigger button imports `AssetPicker` from
 * `@/components/workspace/AssetPicker` — this page is disposable once that
 * lands.
 */

"use client";

import { useState } from "react";
import { AssetPicker } from "@/components/workspace/AssetPicker";

export default function AssetPickerDevPage() {
  const [open, setOpen] = useState(false);
  const [assetId, setAssetId] = useState<string | null>(null);

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">AssetPicker — dev harness</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Trang tạm để kiểm thử AssetPicker (task 5-3) trong trình duyệt thật — chưa
        gắn vào SceneFormPanel thật (xem docstring file này).
      </p>

      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-6 rounded-lg border border-border px-4 py-2 text-sm hover:bg-muted"
      >
        Đổi ảnh…
      </button>

      {assetId && (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="selected-asset-id">
          asset_id đã chọn: {assetId}
        </p>
      )}

      <AssetPicker
        open={open}
        onClose={() => setOpen(false)}
        onAssetSelected={(id) => setAssetId(id)}
        initialStockQuery="GPU datacenter"
        userRole="creator"
        projectAssets={[]}
      />
    </main>
  );
}
