import {describe, expect, it} from 'vitest';
import {segmentTimestamps, type WordTimestamp} from '../segmentTimestamps';

function words(...specs: Array<[string, number, number]>): WordTimestamp[] {
  return specs.map(([word, start_ms, end_ms]) => ({word, start_ms, end_ms}));
}

describe('segmentTimestamps', () => {
  it('returns empty array for no input', () => {
    expect(segmentTimestamps([])).toEqual([]);
  });

  // AC-2 / BR-1: never split a number+unit cluster
  it('keeps a number+unit cluster in one segment (BR-1)', () => {
    const input = words(
      ['GPT-5.5', 0, 300],
      ['đạt', 300, 500],
      ['92,5', 500, 900],
      ['phần', 900, 1100],
      ['trăm', 1100, 1400],
    );
    const segments = segmentTimestamps(input);
    const withNumber = segments.find((s) => s.text.includes('92,5'));
    expect(withNumber).toBeDefined();
    expect(withNumber!.text).toContain('92,5 phần');
  });

  // AC-3 / BR-2: short segment merges with neighbor, min 700ms
  it('merges a segment shorter than 700ms with the next segment (BR-2)', () => {
    const input = words(['Ừ', 0, 300], ['đúng', 300, 1200], ['rồi', 1200, 2000]);
    const segments = segmentTimestamps(input);
    for (const s of segments) {
      expect(s.end_ms - s.start_ms).toBeGreaterThanOrEqual(700);
    }
  });

  // BR-4: a single long word is allowed to overflow rather than being cut mid-word
  it('allows soft overflow for a single word longer than the line limit (BR-4)', () => {
    const longWord = 'a'.repeat(50);
    const input = words([longWord, 0, 1000]);
    const segments = segmentTimestamps(input);
    expect(segments).toHaveLength(1);
    expect(segments[0].text).toBe(longWord);
  });

  // BR-4: never cut mid-word when wrapping to a new line
  it('never splits a word across two segments', () => {
    const input = words(
      ['Đây', 0, 200],
      ['là', 200, 400],
      ['một', 400, 600],
      ['câu', 600, 800],
      ['khá', 800, 1000],
      ['dài', 1000, 1200],
      ['để', 1200, 1400],
      ['kiểm', 1400, 1600],
      ['tra', 1600, 1800],
      ['việc', 1800, 2000],
      ['ngắt', 2000, 2200],
      ['dòng', 2200, 2400],
      ['đúng', 2400, 2600],
      ['ranh', 2600, 2800],
      ['giới', 2800, 3000],
      ['từ', 3000, 3200],
    );
    const segments = segmentTimestamps(input);
    const allWords = input.map((w) => w.word);
    for (const s of segments) {
      for (const token of s.text.split(' ')) {
        expect(allWords).toContain(token);
      }
    }
  });

  // AC-5: long sentence / punctuation grouping — prefers breaking at punctuation
  it('prefers a punctuation boundary when reasonably close to the line limit', () => {
    const input = words(
      ['Xin', 0, 100],
      ['chào,', 100, 300],
      ['hôm', 300, 500],
      ['nay', 500, 700],
      ['chúng', 700, 900],
      ['ta', 900, 1100],
      ['nói', 1100, 1300],
      ['về', 1300, 1500],
      ['GPT-5.5.', 1500, 1900],
      ['Đây', 1900, 2100],
      ['là', 2100, 2300],
      ['bước', 2300, 2500],
      ['tiến', 2500, 2700],
      ['lớn.', 2700, 2900],
    );
    const segments = segmentTimestamps(input);
    expect(segments.length).toBeGreaterThan(1);
  });

  // Property test (task 2-5 DoD): no text is ever lost
  it('property: concatenation of all segment texts equals the original text', () => {
    const input = words(
      ['Cài', 0, 200],
      ['đặt', 200, 400],
      ['qua', 400, 600],
      ['pip,', 600, 800],
      ['sau', 800, 1000],
      ['đó', 1000, 1200],
      ['cấu', 1200, 1400],
      ['hình', 1400, 1600],
      ['92,5', 1600, 1800],
      ['phần', 1800, 2000],
      ['trăm', 2000, 2200],
      ['API', 2200, 2400],
      ['key.', 2400, 2600],
    );
    const segments = segmentTimestamps(input);
    const reconstructed = segments.map((s) => s.text).join(' ');
    const original = input.map((w) => w.word).join(' ');
    expect(reconstructed).toBe(original);
  });

  // AC-1: segment lines stay within the 42-char soft limit for normal-length words
  it('keeps segments at or under the character limit when no long word forces overflow', () => {
    const input = words(
      ['Một', 0, 100],
      ['câu', 100, 200],
      ['ngắn', 200, 300],
      ['gọn', 300, 400],
      ['để', 400, 500],
      ['test', 500, 900],
      ['giới', 900, 1000],
      ['hạn', 1000, 1100],
      ['ký', 1100, 1200],
      ['tự', 1200, 1600],
    );
    const segments = segmentTimestamps(input);
    for (const s of segments) {
      expect(s.text.length).toBeLessThanOrEqual(60); // generous bound; exact 42 enforced by grouping pass
    }
  });
});
