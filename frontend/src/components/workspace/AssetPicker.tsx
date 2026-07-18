/**
 * AssetPicker — "Đổi ảnh" modal, 3 tabs (Task 5-3, FR-20).
 *
 * Every image entering a scene comes through here: Asset dự án (already-used
 * project assets) / Tải lên (upload, BR-2 dedupe) / Tìm stock (BR-1 license
 * badge before select, BR-3 gated on provider keys, BR-4 server-side fetch).
 * On success, `onAssetSelected(assetId)` is called with an internal
 * `asset_id` — the caller writes it into `AssetRef.asset_id` on the scene
 * (never a raw `url`, see rules/security.md + AC4).
 *
 * Follows docs/design/wireframe.html's "Đổi ảnh…" affordance in the scene
 * form's "Ảnh minh hoạ" section. Focus-trap + ESC per a11y (task Step 2).
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ProjectAssetsTab } from "@/components/workspace/AssetPickerTabs/ProjectAssetsTab";
import { UploadTab } from "@/components/workspace/AssetPickerTabs/UploadTab";
import { StockSearchTab } from "@/components/workspace/AssetPickerTabs/StockSearchTab";

export type AssetPickerTabKey = "project" | "upload" | "stock";

export interface AssetPickerProps {
  open: boolean;
  onClose: () => void;
  /** Called with the internal asset_id once an asset is ready to assign. */
  onAssetSelected: (assetId: string) => void;
  /** Prefilled, editable stock query — from media_intent.query_vi. */
  initialStockQuery?: string;
  /** Determines BR-3 messaging: admin -> link Quản trị; creator -> "nhờ admin thêm key". */
  userRole?: "admin" | "creator";
  /** Assets already used in this project (for the Asset dự án tab). */
  projectAssets?: { id: string; thumb_url: string; label: string }[];
}

const TABS: { key: AssetPickerTabKey; label: string }[] = [
  { key: "project", label: "Asset dự án" },
  { key: "upload", label: "Tải lên" },
  { key: "stock", label: "Tìm stock" },
];

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function AssetPicker({
  open,
  onClose,
  onAssetSelected,
  initialStockQuery = "",
  userRole = "creator",
  projectAssets = [],
}: AssetPickerProps) {
  const [activeTab, setActiveTab] = useState<AssetPickerTabKey>(
    initialStockQuery ? "stock" : "project",
  );
  const dialogRef = useRef<HTMLDivElement>(null);

  /* ── ESC to close + focus trap ─────────────────────── */
  useEffect(() => {
    if (!open) return;

    const dialog = dialogRef.current;
    const focusables = dialog
      ? Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      : [];
    focusables[0]?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !dialog) return;

      const els = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      if (els.length === 0) return;
      const first = els[0];
      const last = els[els.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  const handleSelected = useCallback(
    (assetId: string) => {
      onAssetSelected(assetId);
      onClose();
    },
    [onAssetSelected, onClose],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Đổi ảnh"
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl border border-border bg-card"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="text-base font-semibold text-foreground">Đổi ảnh</h2>
          <button
            type="button"
            aria-label="Đóng"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted"
          >
            ✕
          </button>
        </div>

        <div role="tablist" aria-label="Nguồn ảnh" className="flex gap-1 border-b border-border px-5 pt-3">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              className={
                "rounded-t-md px-4 py-2 text-sm font-medium " +
                (activeTab === tab.key
                  ? "border-b-2 border-primary text-foreground"
                  : "text-muted-foreground hover:text-foreground")
              }
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {activeTab === "project" && (
            <ProjectAssetsTab assets={projectAssets} onSelect={handleSelected} />
          )}
          {activeTab === "upload" && <UploadTab onUploaded={handleSelected} />}
          {activeTab === "stock" && (
            <StockSearchTab
              initialQuery={initialStockQuery}
              userRole={userRole}
              onSelected={handleSelected}
            />
          )}
        </div>
      </div>
    </div>
  );
}
