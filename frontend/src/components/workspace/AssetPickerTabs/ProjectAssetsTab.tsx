/**
 * ProjectAssetsTab — reuse an asset already used elsewhere in this project.
 *
 * Deliberately scoped to "assets already referenced by this project's
 * scenes" (a simple reuse list), not a full cross-project asset library
 * screen — that's explicitly out of scope for 5-3 (v1.1, per the task's
 * "thư viện asset workspace-level" scope-out line). The caller supplies the
 * list (derived from the workspace's scenes) — no new backend endpoint.
 */

"use client";

export interface ProjectAsset {
  id: string;
  thumb_url: string;
  label: string;
}

export interface ProjectAssetsTabProps {
  assets: ProjectAsset[];
  onSelect: (assetId: string) => void;
}

export function ProjectAssetsTab({ assets, onSelect }: ProjectAssetsTabProps) {
  if (assets.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Chưa có ảnh nào được dùng trong dự án này. Dùng tab &quot;Tải lên&quot; hoặc
        &quot;Tìm stock&quot; để thêm ảnh đầu tiên.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-4 gap-3" role="list" aria-label="Asset dự án">
      {assets.map((asset) => (
        <button
          key={asset.id}
          type="button"
          role="listitem"
          onClick={() => onSelect(asset.id)}
          className="group flex flex-col gap-1 rounded-lg border border-border p-1 text-left hover:border-primary"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={asset.thumb_url}
            alt={asset.label}
            className="aspect-video w-full rounded-md object-cover"
          />
          <span className="truncate text-xs text-muted-foreground">{asset.label}</span>
        </button>
      ))}
    </div>
  );
}
