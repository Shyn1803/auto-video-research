import {useCurrentFrame, useVideoConfig} from 'remotion';
import type {SubtitleSegment} from '../subtitle/segmentTimestamps';

/**
 * `line`-style subtitle primitive (task 2-5).
 *
 * Segments are computed at props-preparation time via `segmentTimestamps()`
 * (docs/specs/scene-json-schema.md §3.4 — never persisted in Scene JSON) and
 * passed in as `segments`. This component only picks the segment active at
 * the current frame and renders it.
 *
 * BR-3: when `enabled` is false, renders nothing and reserves no layout
 * space — the caller must place this component with `layout="none"` inside
 * a `<Sequence>` (per /remotion-markup guidance) so an absent subtitle never
 * leaves a gap in the flex slot.
 */
export interface SubtitleProps {
  enabled: boolean;
  segments: SubtitleSegment[];
}

/** Pure lookup, exported for unit testing without a React render pass
 * (this package has no jsdom/testing-library setup yet — see 2-5 retrospective). */
export function pickActiveSegment(segments: SubtitleSegment[], currentMs: number): SubtitleSegment | null {
  return segments.find((s) => currentMs >= s.start_ms && currentMs < s.end_ms) ?? null;
}

export const Subtitle = ({enabled, segments}: SubtitleProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  if (!enabled) {
    return null;
  }

  const currentMs = (frame / fps) * 1000;
  const active = pickActiveSegment(segments, currentMs);

  if (!active) {
    return null;
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: '8%',
        right: '8%',
        // Safe-area bottom offset clears TikTok/YouTube Shorts UI chrome
        // (caption bar, like/comment/share rail) per the UI/UX note.
        bottom: '18%',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <span
        style={{
          background: 'rgba(0, 0, 0, 0.6)',
          color: '#ffffff',
          fontSize: 32,
          fontWeight: 600,
          lineHeight: 1.3,
          padding: '6px 16px',
          borderRadius: 8,
          textAlign: 'center',
          maxWidth: '100%',
        }}
      >
        {active.text}
      </span>
    </div>
  );
};
