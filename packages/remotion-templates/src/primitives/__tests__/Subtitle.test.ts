import {describe, expect, it} from 'vitest';
import {pickActiveSegment} from '../Subtitle';
import type {SubtitleSegment} from '../../subtitle/segmentTimestamps';

const segments: SubtitleSegment[] = [
  {text: 'Xin chào', start_ms: 0, end_ms: 1000},
  {text: 'hôm nay chúng ta nói về AI', start_ms: 1000, end_ms: 3500},
];

describe('pickActiveSegment', () => {
  it('picks the segment covering the current time (AC-1 timing)', () => {
    expect(pickActiveSegment(segments, 500)?.text).toBe('Xin chào');
    expect(pickActiveSegment(segments, 1000)?.text).toBe('hôm nay chúng ta nói về AI');
    expect(pickActiveSegment(segments, 3400)?.text).toBe('hôm nay chúng ta nói về AI');
  });

  it('returns null before the first segment or after the last (no stray subtitle)', () => {
    expect(pickActiveSegment(segments, -1)).toBeNull();
    expect(pickActiveSegment(segments, 3500)).toBeNull();
  });

  it('returns null for an empty segment list (BR-3: disabled/no-voice scenes render nothing)', () => {
    expect(pickActiveSegment([], 500)).toBeNull();
  });
});
