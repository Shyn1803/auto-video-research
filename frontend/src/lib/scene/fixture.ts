/**
 * Local fixture Scene JSON for the workspace dev-server walkthrough — no
 * live backend is required to exercise 5-2's controls (same precedent as
 * 5-1's FIXTURE_SCENES in scenes/page.tsx). Each entry is schema-valid
 * against backend/app/schemas/scene.py (bounds per
 * docs/specs/scene-json-schema.md §2's layout catalog).
 *
 * Specialized data-layout elements (BigNumber's `number`, Chart's `chart`,
 * VersusTable's `table`) are not modeled by any 5-2 control — those scenes
 * below only carry `texts`/`images`, which is within each layout's allowed
 * 0-n text/image bounds, but a dedicated editor for those element kinds is
 * out of this task's scope (not asked for in Scope In/Out).
 */

import type { SceneJson } from "./types";

export const SCENE_FIXTURES: Record<string, SceneJson> = {
  "1": {
    scene_id: "1",
    schema_version: "1.0.0",
    scene_number: 1,
    duration_ms: 5000,
    layout: "Hero",
    background: { type: "color", color: "#0F172A" },
    texts: [
      { id: "t1", content: "**AI** đang thay đổi mọi thứ", role: "heading", position: "center", color: "#FFFFFF", animation: { type: "fade_in", delay_ms: 0, duration_ms: 400 } },
    ],
    images: [],
    voice: { text: "AI đang thay đổi mọi thứ chúng ta biết.", voice_id: "vi-VN-female-1", speed: 1.0, audio: { path: "s3://voice/1.mp3", duration_ms: 4800, timestamps: [] } },
    subtitle: { enabled: true, style: "line" },
    transition: { type: "fade", duration_ms: 400 },
  },
  "2": {
    scene_id: "2",
    schema_version: "1.0.0",
    scene_number: 2,
    duration_ms: 6000,
    layout: "MediaText",
    background: { type: "color", color: "#111827" },
    texts: [
      { id: "t1", content: "Bức ảnh minh hoạ", role: "heading", position: "top", color: "#FFFFFF" },
      { id: "t2", content: "Giải thích chi tiết hơn ở đây", role: "body", position: "center", color: "#E5E7EB" },
      { id: "t3", content: "Ghi chú thêm", role: "caption", position: "bottom", color: "#9CA3AF" },
    ],
    images: [{ id: "i1", asset: { asset_id: "demo-asset-1" }, fit: "cover", ken_burns: true }],
    voice: { text: "Đây là phần giải thích chi tiết.", voice_id: "vi-VN-male-1", speed: 1.0, audio: null },
    subtitle: { enabled: true, style: "line" },
    transition: { type: "slide_left", duration_ms: 300 },
  },
  "3": {
    scene_id: "3",
    schema_version: "1.0.0",
    scene_number: 3,
    duration_ms: 6000,
    layout: "Chart",
    background: { type: "color", color: "#0F172A" },
    texts: [{ id: "t1", content: "Tăng trưởng theo quý", role: "heading", position: "top", color: "#FFFFFF" }],
    images: [],
    voice: { text: "Biểu đồ cho thấy tăng trưởng theo quý.", voice_id: "vi-VN-female-1", speed: 1.0, audio: { path: "s3://voice/3.mp3", duration_ms: 5800, timestamps: [] } },
    subtitle: { enabled: true, style: "line" },
    transition: { type: "fade", duration_ms: 400 },
  },
  "4": {
    scene_id: "4",
    schema_version: "1.0.0",
    scene_number: 4,
    duration_ms: 5000,
    layout: "BigNumber",
    background: { type: "color", color: "#0F172A" },
    texts: [{ id: "t1", content: "Tổng người dùng", role: "caption", position: "bottom", color: "#FFFFFF" }],
    images: [],
    voice: { text: "Con số ấn tượng về người dùng.", voice_id: "vi-VN-male-1", speed: 1.0, audio: { path: "s3://voice/4.mp3", duration_ms: 4700, timestamps: [] } },
    subtitle: { enabled: true, style: "line" },
    transition: { type: "zoom", duration_ms: 400 },
  },
  "5": {
    scene_id: "5",
    schema_version: "1.0.0",
    scene_number: 5,
    duration_ms: 6000,
    layout: "VersusTable",
    background: { type: "color", color: "#0F172A" },
    texts: [{ id: "t1", content: "So sánh 2 mô hình", role: "heading", position: "top", color: "#FFFFFF" }],
    images: [],
    voice: { text: "So sánh hai mô hình phổ biến.", voice_id: "vi-VN-female-1", speed: 1.0, audio: null },
    subtitle: { enabled: true, style: "line" },
    transition: { type: "none", duration_ms: 200 },
  },
};
