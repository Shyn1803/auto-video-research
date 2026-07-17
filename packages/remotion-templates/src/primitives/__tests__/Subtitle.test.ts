import { describe, expect, it } from 'vitest';
import { resolveSubtitleRenderState, type SubtitleSpec } from '../Subtitle';
import type { SubtitleSegment } from '../../subtitle/segmentTimestamps';

const segments: SubtitleSegment[] = [
  { text: 'Xin chào các bạn', start_ms: 0, end_ms: 1500 },
  { text: 'hôm nay trời đẹp', start_ms: 1500, end_ms: 3000 },
];

describe('resolveSubtitleRenderState', () => {
  // ── BR-3: disabled subtitle renders nothing, no layout space ───────────

  it('returns null when subtitle.enabled is false (BR-3)', () => {
    const spec: SubtitleSpec = { enabled: false, style: 'line' };
    expect(resolveSubtitleRenderState(spec, segments, 500)).toBeNull();
  });

  it('returns null for an unsupported style', () => {
    const spec = { enabled: true, style: 'karaoke' } as unknown as SubtitleSpec;
    expect(resolveSubtitleRenderState(spec, segments, 500)).toBeNull();
  });

  // ── enabled: shows the active segment at the given time ────────────────

  it('shows the first segment during its time window', () => {
    const spec: SubtitleSpec = { enabled: true, style: 'line' };
    const state = resolveSubtitleRenderState(spec, segments, 500);
    expect(state?.text).toBe('Xin chào các bạn');
  });

  it('switches to the second segment once its window starts', () => {
    const spec: SubtitleSpec = { enabled: true, style: 'line' };
    const state = resolveSubtitleRenderState(spec, segments, 2000);
    expect(state?.text).toBe('hôm nay trời đẹp');
  });

  it('returns null before the first segment or after the last one', () => {
    const spec: SubtitleSpec = { enabled: true, style: 'line' };
    expect(resolveSubtitleRenderState(spec, segments, -10)).toBeNull();
    expect(resolveSubtitleRenderState(spec, segments, 5000)).toBeNull();
  });

  it('returns null when there are no segments at all (e.g. silent scene)', () => {
    const spec: SubtitleSpec = { enabled: true, style: 'line' };
    expect(resolveSubtitleRenderState(spec, [], 500)).toBeNull();
  });
});
