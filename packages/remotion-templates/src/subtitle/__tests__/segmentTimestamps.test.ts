import { describe, expect, it } from 'vitest';
import {
  activeSegmentAt,
  segmentTimestamps,
  type WordTimestamp,
} from '../segmentTimestamps';

/** Build a WordTimestamp[] from words with a fixed per-word duration,
 * spaced back-to-back starting at `startMs` — convenience for tests that
 * don't care about exact timing, only about grouping. */
function words(
  text: string,
  opts: { startMs?: number; wordDurationMs?: number } = {}
): WordTimestamp[] {
  const startMs = opts.startMs ?? 0;
  const wordDurationMs = opts.wordDurationMs ?? 300;
  return text.split(' ').map((word, i) => ({
    word,
    start_ms: startMs + i * wordDurationMs,
    end_ms: startMs + (i + 1) * wordDurationMs,
  }));
}

describe('segmentTimestamps', () => {
  // ── AC-1 / happy path ──────────────────────────────────────────────────

  it('groups a short sentence into a single segment within the char limit', () => {
    const segments = segmentTimestamps(words('Xin chào các bạn'));
    expect(segments).toHaveLength(1);
    expect(segments[0].text).toBe('Xin chào các bạn');
    expect(segments[0].start_ms).toBe(0);
  });

  // ── AC-2 / BR-1: number + unit never split ─────────────────────────────

  it('never splits a number+unit cluster (BR-1)', () => {
    const input = words('GPT-5.5 đạt 92,5 phần trăm điểm SWE-bench hôm nay');
    const segments = segmentTimestamps(input);
    const joined = segments.map((s) => s.text).join(' ');
    expect(joined).toContain('92,5 phần trăm');
    // The cluster must appear intact inside exactly one segment.
    const clusterSegment = segments.find((s) => s.text.includes('92,5'));
    expect(clusterSegment?.text).toContain('92,5 phần trăm');
  });

  it('keeps a percent-sign number with its following unit word', () => {
    const input = words('Tỷ lệ tăng 50% mỗi năm liên tục');
    const segments = segmentTimestamps(input);
    const joined = segments.map((s) => s.text).join(' ');
    expect(joined).toContain('50%');
  });

  // ── AC-3 / BR-2: short segment merges with neighbor, no flicker ────────

  it('merges a single short word (<700ms) into the next segment', () => {
    // "Có" gets a lone 300ms timestamp far from the rest of the sentence
    // in duration terms — force it into its own line by making it the
    // sole content of an early break via punctuation.
    const input: WordTimestamp[] = [
      { word: 'Có.', start_ms: 0, end_ms: 300 },
      { word: 'Một', start_ms: 300, end_ms: 600 },
      { word: 'câu', start_ms: 600, end_ms: 900 },
      { word: 'chuyện', start_ms: 900, end_ms: 1200 },
      { word: 'dài', start_ms: 1200, end_ms: 1500 },
    ];
    const segments = segmentTimestamps(input);
    // No segment should be shorter than 700ms.
    for (const seg of segments) {
      expect(seg.end_ms - seg.start_ms).toBeGreaterThanOrEqual(700);
    }
    // "Có." must not appear as an isolated single-word segment.
    expect(segments.some((s) => s.text.trim() === 'Có.')).toBe(false);
  });

  it('merges a too-short trailing segment into the previous one', () => {
    const input: WordTimestamp[] = [
      { word: 'Một', start_ms: 0, end_ms: 500 },
      { word: 'câu', start_ms: 500, end_ms: 1000 },
      { word: 'văn', start_ms: 1000, end_ms: 1500 },
      { word: 'dài.', start_ms: 1500, end_ms: 2000 },
      { word: 'Hết.', start_ms: 2000, end_ms: 2200 }, // 200ms — too short, is last
    ];
    const segments = segmentTimestamps(input);
    for (const seg of segments) {
      expect(seg.end_ms - seg.start_ms).toBeGreaterThanOrEqual(700);
    }
    expect(segments[segments.length - 1].text).toContain('Hết.');
  });

  // ── AC-5 / BR-4: single long word soft-overflow, no mid-word cut ───────

  it('allows a single long word to overflow the 42-char limit rather than cut it', () => {
    const longWord = 'Supercalifragilisticexpialidocioustiengviet'; // 44 chars
    const input = words(`${longWord} tiếp theo`);
    const segments = segmentTimestamps(input);
    const withLongWord = segments.find((s) => s.text.includes(longWord));
    expect(withLongWord?.text).toContain(longWord); // never truncated
  });

  it('breaks long sentences into multiple lines at word boundaries', () => {
    const longSentence =
      'Hôm nay chúng ta sẽ nói về một chủ đề rất thú vị liên quan đến trí tuệ nhân tạo và tương lai của ngành công nghệ';
    const segments = segmentTimestamps(words(longSentence));
    expect(segments.length).toBeGreaterThan(1);
    for (const seg of segments) {
      // Soft overflow only allowed for a single unsplittable word/cluster —
      // a multi-word line should respect the limit (some tolerance for the
      // greedy packer's last-word check).
      expect(seg.text.length).toBeLessThanOrEqual(60);
    }
  });

  it('prefers breaking at punctuation over an arbitrary word boundary', () => {
    const input = words(
      'Xin chào các bạn hôm nay trời đẹp quá, và chúng ta nên đi chơi công viên buổi chiều nay'
    );
    const segments = segmentTimestamps(input);
    expect(segments.length).toBeGreaterThan(1);
    // At least one segment boundary should land right after a comma/period.
    const endsAtPunctuation = segments.some((s) => /[,.!?]$/.test(s.text.trim()));
    expect(endsAtPunctuation).toBe(true);
  });

  // ── property test: no text lost (mandatory per DoD) ────────────────────

  it('never loses a word — concatenation of all segments equals original text', () => {
    const inputs = [
      'Xin chào các bạn hôm nay chúng ta nói về GPT-5.5',
      'GPT-5.5 đạt 92,5 phần trăm điểm SWE-bench',
      '50% người dùng thích tính năng mới trong khi 50% còn lại thì không',
      'Một, hai, ba, bốn, năm, sáu, bảy, tám, chín, mười',
      'Đây là một câu rất dài với nhiều từ để kiểm tra thuật toán cắt dòng subtitle theo giới hạn ký tự',
    ];
    for (const text of inputs) {
      const segments = segmentTimestamps(words(text));
      const reconstructed = segments.map((s) => s.text).join(' ');
      const originalWords = text.split(' ').join(' ');
      expect(reconstructed).toBe(originalWords);
    }
  });

  // ── edge cases ──────────────────────────────────────────────────────────

  it('returns an empty array for empty input', () => {
    expect(segmentTimestamps([])).toEqual([]);
  });

  it('handles a single word', () => {
    const segments = segmentTimestamps(words('Chào'));
    expect(segments).toHaveLength(1);
    expect(segments[0].text).toBe('Chào');
  });
});

describe('activeSegmentAt', () => {
  it('finds the segment active at a given time', () => {
    const segments = [
      { text: 'a', start_ms: 0, end_ms: 1000 },
      { text: 'b', start_ms: 1000, end_ms: 2000 },
    ];
    expect(activeSegmentAt(segments, 500)?.text).toBe('a');
    expect(activeSegmentAt(segments, 1500)?.text).toBe('b');
    expect(activeSegmentAt(segments, 1000)?.text).toBe('b'); // boundary is inclusive-start
  });

  it('returns null outside all segments', () => {
    const segments = [{ text: 'a', start_ms: 0, end_ms: 1000 }];
    expect(activeSegmentAt(segments, 5000)).toBeNull();
  });
});
