/**
 * StockSearchTab — search stock photos, license badge before selection (BR-1),
 * gated on provider keys (BR-3), server-side fetch on select (BR-4).
 *
 * Query prefilled from media_intent.query_vi but editable (task scope). BR-3:
 * if no asset_stock provider is active, the tab is disabled with a
 * role-appropriate explanation (admin -> link Quản trị; creator -> nhờ admin
 * thêm key) rather than a blank/broken search box.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchStockAsset,
  fetchStockStatus,
  searchStock,
  type StockSearchResult,
} from "@/lib/api/assets";

export interface StockSearchTabProps {
  initialQuery?: string;
  userRole?: "admin" | "creator";
  onSelected: (assetId: string) => void;
}

type Phase = "checking" | "disabled" | "ready" | "searching" | "fetching" | "error";

export function StockSearchTab({
  initialQuery = "",
  userRole = "creator",
  onSelected,
}: StockSearchTabProps) {
  const [query, setQuery] = useState(initialQuery);
  const [phase, setPhase] = useState<Phase>("checking");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  /* ── BR-3: gate the whole tab on provider key/health status ───────── */
  useEffect(() => {
    let cancelled = false;
    fetchStockStatus()
      .then((status) => {
        if (cancelled) return;
        setPhase(status.active ? "ready" : "disabled");
      })
      .catch(() => {
        if (!cancelled) setPhase("disabled");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runSearch = useCallback(async () => {
    if (!query.trim()) return;
    setPhase("searching");
    setError(null);
    try {
      const found = await searchStock(query);
      setResults(found);
      setActiveIndex(0);
      setPhase("ready");
    } catch {
      setError("Tìm kiếm thất bại. Thử lại sau.");
      setPhase("ready");
    }
  }, [query]);

  useEffect(() => {
    if (phase === "ready" && initialQuery && results.length === 0 && !error) {
      void runSearch();
    }
    // Only auto-run once, right when the tab becomes ready — not on every
    // `results`/`error` change (those are set BY this same effect's run).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const selectResult = useCallback(
    async (result: StockSearchResult) => {
      setPhase("fetching");
      setError(null);
      try {
        const asset = await fetchStockAsset({
          url: result.url,
          provider: result.provider,
          license: result.license,
          attribution: result.attribution,
          attribution_required: true,
        });
        onSelected(asset.id);
      } catch {
        setError("Không lấy được ảnh này. Thử ảnh khác.");
        setPhase("ready");
      }
    },
    [onSelected],
  );

  if (phase === "checking") {
    return <p className="text-sm text-muted-foreground">Đang kiểm tra nguồn stock…</p>;
  }

  if (phase === "disabled") {
    return (
      <div className="rounded-lg border border-border p-4 text-sm text-muted-foreground">
        <p className="mb-2 font-medium text-foreground">Chưa có nguồn ảnh stock nào hoạt động.</p>
        {userRole === "admin" ? (
          <a href="/admin/providers" className="text-primary underline">
            Vào Quản trị để thêm API key
          </a>
        ) : (
          <p>Nhờ admin thêm key cho Pexels/Pixabay/Unsplash.</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void runSearch();
        }}
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tìm ảnh stock…"
          className="flex-1 rounded-md border border-border px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={phase === "searching" || phase === "fetching"}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Tìm
        </button>
      </form>

      {phase === "searching" && <p className="text-sm text-muted-foreground">Đang tìm…</p>}
      {phase === "fetching" && (
        <p className="text-sm text-muted-foreground" role="status">
          Đang lấy ảnh…
        </p>
      )}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {results.length > 0 && (
        <div
          ref={gridRef}
          role="grid"
          aria-label="Kết quả tìm stock"
          className="grid grid-cols-3 gap-3"
          onKeyDown={(e) => {
            const cols = 3;
            let next = activeIndex;
            if (e.key === "ArrowRight") next = Math.min(activeIndex + 1, results.length - 1);
            else if (e.key === "ArrowLeft") next = Math.max(activeIndex - 1, 0);
            else if (e.key === "ArrowDown")
              next = Math.min(activeIndex + cols, results.length - 1);
            else if (e.key === "ArrowUp") next = Math.max(activeIndex - cols, 0);
            else if (e.key === "Enter") {
              void selectResult(results[activeIndex]);
              return;
            } else return;
            e.preventDefault();
            setActiveIndex(next);
          }}
        >
          {results.map((result, idx) => (
            <button
              key={`${result.provider}-${result.url}`}
              type="button"
              role="gridcell"
              tabIndex={idx === activeIndex ? 0 : -1}
              disabled={phase === "fetching"}
              onFocus={() => setActiveIndex(idx)}
              onClick={() => void selectResult(result)}
              className={
                "group flex flex-col gap-1 rounded-lg border p-1 text-left " +
                (idx === activeIndex ? "border-primary" : "border-border hover:border-primary")
              }
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={result.thumb_url}
                alt={`${result.attribution || result.provider} — ${result.license}`}
                className="aspect-video w-full rounded-md object-cover"
              />
              <div className="flex items-center justify-between gap-1 px-1">
                <span className="truncate text-xs text-muted-foreground">
                  {result.attribution || result.provider}
                </span>
                <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground">
                  {result.license}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
