/**
 * TypeScript mirror of the resolved Scene JSON render contract
 * (backend/app/schemas/scene.py). Field names/shapes/bounds must match that
 * Pydantic model exactly — this is a hand-authored mirror (not yet
 * codegen'd from the exported JSON Schema, unlike the Remotion Zod schema
 * in packages/remotion-templates/src/schema.ts) because this file only
 * needs the editor-relevant subset. If scene.py changes, update this file
 * in the same PR (rules/documentation.md "đổi contract").
 */

import type { AnimationType, TextPosition, TextRole } from "./constants";

export interface AnimationJson {
  type: AnimationType;
  delay_ms: number;
  duration_ms: number;
}

export interface TextElementJson {
  id: string;
  content: string;
  role: TextRole;
  position: TextPosition;
  color?: string | null;
  highlight_color?: string | null;
  animation?: AnimationJson | null;
}

export interface ImageElementJson {
  id: string;
  asset: { asset_id?: string | null; url?: string | null };
  fit?: "cover" | "contain";
  ken_burns?: boolean;
  caption?: string | null;
  animation?: AnimationJson | null;
}

export interface AudioSpecJson {
  path: string;
  duration_ms: number;
  timestamps: { word: string; start_ms: number; end_ms: number }[];
}

export interface VoiceSpecJson {
  text: string;
  voice_id: string;
  speed: number;
  audio?: AudioSpecJson | null;
}

export interface TransitionJson {
  type: "none" | "fade" | "slide_left" | "slide_up" | "zoom";
  duration_ms: number;
}

export interface SceneJson {
  scene_id: string;
  schema_version: string;
  scene_number: number;
  duration_ms: number;
  layout: string;
  background: { type: "color"; color: string } | Record<string, unknown>;
  texts: TextElementJson[];
  images: ImageElementJson[];
  voice?: VoiceSpecJson | null;
  subtitle?: { enabled: boolean; style: "line" | "karaoke" };
  transition: TransitionJson;
  motion_plan?: unknown;
  layout_override?: string | null;
}
