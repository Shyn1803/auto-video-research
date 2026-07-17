import {segmentTimestamps, type WordTimestamp, type SubtitleSegment} from './segmentTimestamps';

/**
 * Props-preparation step for the `Subtitle` primitive (task 2-5, Step 4).
 *
 * Mirrors `VoiceSpec`/`SubtitleSpec` from `backend/app/schemas/scene.py` — field
 * names match exactly to avoid drift (no generated TS type exists yet for the
 * full Scene model; `schema.ts` only emits a runtime zod validator, see
 * src/__tests__/schema.fixtures.test.ts). Segments are computed here, at
 * render/preview props-preparation time, and are never persisted in Scene
 * JSON (docs/specs/scene-json-schema.md §3.4).
 */
export interface VoiceSpecInput {
  audio?: {
    timestamps: WordTimestamp[];
  } | null;
}

export interface SubtitleSpecInput {
  enabled: boolean;
  style: 'line' | 'karaoke';
}

export interface PreparedSubtitleProps {
  enabled: boolean;
  segments: SubtitleSegment[];
}

/**
 * Decisions already locked (task 2-5): subtitle is on by default for every
 * scene that has voice. `enabled` is false when the scene has no voice/audio
 * timestamps yet (nothing to segment) or when `subtitle.enabled` is
 * explicitly false (BR-3) or the style isn't the supported `line` style
 * (karaoke is out of scope — v2, scene-json-schema.md §3.6).
 */
export function prepareSubtitleProps(
  voice: VoiceSpecInput | null | undefined,
  subtitle: SubtitleSpecInput,
): PreparedSubtitleProps {
  const timestamps = voice?.audio?.timestamps ?? [];
  if (!subtitle.enabled || subtitle.style !== 'line' || timestamps.length === 0) {
    return {enabled: false, segments: []};
  }
  return {enabled: true, segments: segmentTimestamps(timestamps)};
}
