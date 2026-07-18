/**
 * Assets API client — AssetPicker (Task 5-3, FR-20).
 *
 * Mirrors backend/app/api/assets.py. Kept hand-written (not yet generated
 * from OpenAPI, unlike other clients per rules/code-style.md) because no
 * `make gen-api-client` step exists in this repo yet — flagged as a
 * follow-up once that tooling lands, not invented here.
 */

import { api } from "@/lib/api/interceptor";

export interface StockSearchResult {
  provider: string;
  url: string;
  thumb_url: string;
  attribution: string;
  attribution_url: string;
  license: string;
  width: string;
  height: string;
}

export interface StockStatus {
  active: boolean;
  providers: string[];
}

export interface AssetResponse {
  id: string;
  provider: string;
  license: string;
  attribution_required: boolean;
  attribution_text: string | null;
  storage_path: string;
  content_hash: string;
  reused: boolean;
}

export async function fetchStockStatus(): Promise<StockStatus> {
  const res = await api.get<StockStatus>("/assets/stock-status");
  return res.data;
}

export async function searchStock(query: string): Promise<StockSearchResult[]> {
  const res = await api.get<StockSearchResult[]>("/assets/search", {
    params: { q: query },
  });
  return res.data;
}

export async function uploadAsset(file: File): Promise<AssetResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post<AssetResponse>("/assets/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export interface FetchStockPayload {
  url: string;
  provider: string;
  license: string;
  attribution?: string;
  attribution_required?: boolean;
}

export async function fetchStockAsset(payload: FetchStockPayload): Promise<AssetResponse> {
  const res = await api.post<AssetResponse>("/assets/fetch-stock", payload);
  return res.data;
}
