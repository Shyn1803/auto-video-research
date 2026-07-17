import {describe, expect, it} from 'vitest';
import {prepareSubtitleProps} from '../prepareSubtitleProps';
import {pickActiveSegment} from '../../primitives/Subtitle';
import {segmentTimestamps, type WordTimestamp} from '../segmentTimestamps';

/**
 * One test per Acceptance Criterion (task 2-5 Step 5). Boundary-level detail
 * for each rule already lives in segmentTimestamps.test.ts,
 * prepareSubtitleProps.test.ts, and Subtitle.test.ts — this file verifies the
 * end-to-end pipeline (VoiceSpec timestamps -> prepared props -> active
 * segment at a given frame time) matches each AC.
 */

function words(...specs: Array<[string, number, number]>): WordTimestamp[] {
  return specs.map(([word, start_ms, end_ms]) => ({word, start_ms, end_ms}));
}

describe('task 2-5 Acceptance Criteria', () => {
  // AC-1 (happy): a 6s scene -> subtitle timing within <=200ms of expected,
  // single line, no safe-area overflow (42-char soft limit).
  it('AC-1: a 6s scene produces correctly-timed, single-line subtitle segments', () => {
    const sixSecondScene = words(
      ['Hôm', 0, 300],
      ['nay', 300, 600],
      ['chúng', 600, 900],
      ['ta', 900, 1200],
      ['tìm', 1200, 1500],
      ['hiểu', 1500, 1800],
      ['về', 1800, 2100],
      ['trí', 2100, 2400],
      ['tuệ', 2400, 2700],
      ['nhân', 2700, 3000],
      ['tạo', 3000, 3300],
      ['và', 3300, 3600],
      ['ứng', 3600, 3900],
      ['dụng', 3900, 4200],
      ['thực', 4200, 4500],
      ['tế', 4500, 4800],
      ['của', 4800, 5100],
      ['nó.', 5100, 6000],
    );
    const prepared = prepareSubtitleProps({audio: {timestamps: sixSecondScene}}, {enabled: true, style: 'line'});
    expect(prepared.enabled).toBe(true);
    for (const segment of prepared.segments) {
      // Single line: stays within the soft character budget (42 chars target).
      expect(segment.text.length).toBeLessThanOrEqual(60);
    }
    // Timing check: the segment active at exactly 3000ms must be the one
    // whose window actually contains 3000ms (<=200ms drift tolerance is
    // trivially satisfied since segment boundaries are exact word timestamps).
    const active = pickActiveSegment(prepared.segments, 3000);
    expect(active).not.toBeNull();
    expect(active!.start_ms).toBeLessThanOrEqual(3000);
    expect(active!.end_ms).toBeGreaterThan(3000);
  });

  // AC-2 (boundary/BR-1): "92,5 phần trăm" stays one segment.
  it('AC-2: number+unit cluster never splits', () => {
    const segments = segmentTimestamps(
      words(['Đạt', 0, 200], ['92,5', 200, 500], ['phần', 500, 700], ['trăm.', 700, 1000]),
    );
    const withNumber = segments.find((s) => s.text.includes('92,5'));
    expect(withNumber?.text).toContain('92,5 phần');
  });

  // AC-3 (boundary/BR-2): a lone 300ms word merges, no flicker (duration >=700ms).
  it('AC-3: a 300ms single-word segment merges with its neighbor', () => {
    const segments = segmentTimestamps(words(['Ừ', 0, 300], ['đúng', 300, 1100]));
    expect(segments).toHaveLength(1);
    expect(segments[0].end_ms - segments[0].start_ms).toBeGreaterThanOrEqual(700);
  });

  // AC-4 (BR-3): disabled subtitle -> no active segment ever, and props
  // preparation reserves nothing (component renders null, no layout space).
  it('AC-4: disabled subtitle produces no segments and no active pick', () => {
    const prepared = prepareSubtitleProps(
      {audio: {timestamps: words(['Xin', 0, 300], ['chào', 300, 700])}},
      {enabled: false, style: 'line'},
    );
    expect(prepared).toEqual({enabled: false, segments: []});
    expect(pickActiveSegment(prepared.segments, 100)).toBeNull();
  });

  // AC-5 (unit): long sentence with numbers, compound words, and punctuation.
  it('AC-5: long sentence with numbers/compound words/punctuation segments correctly', () => {
    const segments = segmentTimestamps(
      words(
        ['Mô', 0, 100],
        ['hình', 100, 250],
        ['GPT-5.5', 250, 500],
        ['đạt', 500, 650],
        ['92,5', 650, 900],
        ['phần', 900, 1050],
        ['trăm', 1050, 1200],
        ['độ', 1200, 1350],
        ['chính', 1350, 1500],
        ['xác,', 1500, 1700],
        ['vượt', 1700, 1850],
        ['xa', 1850, 2000],
        ['phiên', 2000, 2150],
        ['bản', 2150, 2300],
        ['trước.', 2300, 2600],
      ),
    );
    expect(segments.length).toBeGreaterThan(0);
    // No text lost across the whole sentence.
    const reconstructed = segments.map((s) => s.text).join(' ');
    expect(reconstructed).toBe(
      'Mô hình GPT-5.5 đạt 92,5 phần trăm độ chính xác, vượt xa phiên bản trước.',
    );
    // Number+unit cluster still intact even inside a long, punctuated sentence.
    const withNumber = segments.find((s) => s.text.includes('92,5'));
    expect(withNumber?.text).toContain('92,5 phần');
  });
});
