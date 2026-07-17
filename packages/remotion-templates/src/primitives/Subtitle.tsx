import {Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {activeSegmentAt, type SubtitleSegment} from '../subtitle/segmentTimestamps';

export interface SubtitleSpec {
  enabled: boolean;
  style: 'line';
}

export interface SubtitleProps {
  subtitle: SubtitleSpec;
  segments: SubtitleSegment[];
  /** Scene-relative time in ms this Subtitle instance is mounted at — added
   * to the current frame's local time to get an absolute scene time, so the
   * component works whether it's rendered top-level or inside a Sequence. */
  sceneStartMs?: number;
}

const FADE_FRAMES = 4;

/**
 * Pure decision logic for the `line` subtitle style, extracted out of the
 * component so it's testable without a Remotion render context (this
 * package's tests are logic-only, no React/DOM test runner is set up —
 * see src/__tests__/scene-renderer.test.ts for the existing convention).
 *
 * BR-3: `subtitle.enabled === false` (or an unsupported style) resolves to
 * `null` — the component must render nothing and reserve no layout space.
 */
export function resolveSubtitleRenderState(
  subtitle: SubtitleSpec,
  segments: SubtitleSegment[],
  timeMs: number
): {text: string; segmentStartMs: number} | null {
  if (!subtitle.enabled || subtitle.style !== 'line') {
    return null;
  }
  const active = activeSegmentAt(segments, timeMs);
  if (!active) {
    return null;
  }
  return {text: active.text, segmentStartMs: active.start_ms};
}

/**
 * `line` subtitle style (task 2-5) — one line of text near the bottom of the
 * frame, inside the safe area (below TikTok/YouTube UI chrome), dark
 * translucent background so it reads over any visual. Segments are computed
 * by `segmentTimestamps()` at render/preview time, never stored in Scene
 * JSON (spec §3.4).
 */
export const Subtitle = ({subtitle, segments, sceneStartMs = 0}: SubtitleProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const timeMs = sceneStartMs + (frame / fps) * 1000;
  const state = resolveSubtitleRenderState(subtitle, segments, timeMs);

  if (!state) {
    return null;
  }

  // Quick fade at the very start of a segment so consecutive segments don't
  // hard-cut — kept short enough it never registers as a visible animation.
  const segmentStartFrame = ((state.segmentStartMs - sceneStartMs) / 1000) * fps;
  const opacity = interpolate(
    frame,
    [segmentStartFrame, segmentStartFrame + FADE_FRAMES],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    }
  );

  return (
    <div
      data-testid="subtitle-line"
      style={{
        position: 'absolute',
        left: '8%',
        right: '8%',
        // Sits above TikTok/YouTube Shorts UI chrome (share/like rail,
        // caption/progress bar) without a per-platform safe-area table yet
        // (v1.1 scope) — a fixed generous bottom margin covers both.
        bottom: '14%',
        display: 'flex',
        justifyContent: 'center',
        opacity,
      }}
    >
      <span
        style={{
          maxWidth: '100%',
          padding: '8px 16px',
          borderRadius: 8,
          backgroundColor: 'rgba(0, 0, 0, 0.65)',
          color: '#ffffff',
          fontSize: 34,
          fontWeight: 600,
          lineHeight: 1.3,
          textAlign: 'center',
          whiteSpace: 'pre-wrap',
          wordBreak: 'keep-all',
        }}
      >
        {state.text}
      </span>
    </div>
  );
};
