/**
 * Subtitle segmentation — task 2-5 (FR-19).
 *
 * Groups per-word timestamps (scene-json-schema.md §3.4 `voice.audio.timestamps`
 * shape: `{ word, start_ms, end_ms }`) into display segments for the `line`
 * subtitle style. Pure function, computed at render/preview time — segments
 * are NEVER stored in Scene JSON (spec §3.4).
 *
 * `@remotion/captions`' `createTikTokStyleCaptions()` was evaluated first
 * (dev-guide.md §2.1 mandatory check, /remotion-captions skill) and rejected:
 * it groups tokens purely by a time window (`combineTokensWithinMilliseconds`),
 * with no character-length limit and no linguistic awareness of Vietnamese
 * number+unit clusters — a numeric token and its unit word only stay together
 * by coincidence of timing, not because the package understands they form one
 * unit. That's exactly BR-1's requirement ("92,5 phần trăm" must never split
 * across a line), so a custom algorithm is used instead. See
 * `.claude/tasks/state/2-5.json` decisions[] for the recorded evaluation.
 */

export interface WordTimestamp {
  word: string;
  start_ms: number;
  end_ms: number;
}

export interface SubtitleSegment {
  text: string;
  start_ms: number;
  end_ms: number;
}

const MAX_CHARS_PER_LINE = 42;
const MIN_SEGMENT_DURATION_MS = 700;

// Common Vietnamese unit/measure words that may follow a numeral — BR-1:
// a numeral immediately followed by one of these must never be split onto
// separate segments. Not exhaustive by design (v1 scope); extend here if a
// new news-script unit shows up in practice.
const UNIT_WORDS = new Set([
  "phần",
  "trăm",
  "%",
  "độ",
  "mét",
  "km",
  "kg",
  "g",
  "giờ",
  "phút",
  "giây",
  "usd",
  "vnd",
  "đồng",
  "người",
  "lần",
  "tỷ",
  "triệu",
  "nghìn",
  "ngày",
  "tháng",
  "năm",
]);

// Punctuation that marks a preferred break point when a line is close to
// the character limit — prefer breaking here over an arbitrary word boundary.
const SENTENCE_PUNCTUATION = /[.!?…]$/;
const CLAUSE_PUNCTUATION = /[,;:]$/;

function isNumericToken(word: string): boolean {
  return /^[+-]?\d+([.,]\d+)?%?$/.test(word);
}

/**
 * A "cluster" is one or more consecutive word timestamps that must always
 * stay in the same segment (BR-1). A plain word is a cluster of size 1.
 */
interface Cluster {
  text: string;
  start_ms: number;
  end_ms: number;
}

function buildClusters(words: WordTimestamp[]): Cluster[] {
  const clusters: Cluster[] = [];
  let i = 0;
  while (i < words.length) {
    const current = words[i];
    if (isNumericToken(current.word)) {
      // Greedily absorb following unit words into this numeral's cluster.
      let j = i + 1;
      const parts = [current.word];
      let end_ms = current.end_ms;
      while (j < words.length && UNIT_WORDS.has(words[j].word.toLowerCase())) {
        parts.push(words[j].word);
        end_ms = words[j].end_ms;
        j += 1;
      }
      clusters.push({ text: parts.join(" "), start_ms: current.start_ms, end_ms });
      i = j;
    } else {
      clusters.push({ text: current.word, start_ms: current.start_ms, end_ms: current.end_ms });
      i += 1;
    }
  }
  return clusters;
}

/** Greedily pack clusters into ≤42-char lines, preferring punctuation breaks
 * (BR-4: a single cluster longer than the limit is kept whole — soft overflow). */
function packIntoLines(clusters: Cluster[]): Cluster[][] {
  const lines: Cluster[][] = [];
  let current: Cluster[] = [];
  let currentLen = 0;

  for (const cluster of clusters) {
    const addedLen = (currentLen > 0 ? 1 : 0) + cluster.text.length; // +1 for the joining space
    const wouldExceed = currentLen + addedLen > MAX_CHARS_PER_LINE;

    if (current.length === 0) {
      // Always place at least one cluster on a line, even if it alone
      // overflows (BR-4: never cut mid-word/mid-cluster).
      current.push(cluster);
      currentLen = cluster.text.length;
      continue;
    }

    if (wouldExceed) {
      lines.push(current);
      current = [cluster];
      currentLen = cluster.text.length;
      continue;
    }

    current.push(cluster);
    currentLen += addedLen;

    const lastText = cluster.text;
    const atSentenceBreak = SENTENCE_PUNCTUATION.test(lastText);
    const atClauseBreak = CLAUSE_PUNCTUATION.test(lastText);
    // Prefer breaking at a punctuation boundary once the line carries a
    // reasonable amount of text, rather than always filling to the limit.
    if ((atSentenceBreak || atClauseBreak) && currentLen >= MAX_CHARS_PER_LINE * 0.6) {
      lines.push(current);
      current = [];
      currentLen = 0;
    }
  }
  if (current.length > 0) lines.push(current);
  return lines;
}

function linesToSegments(lines: Cluster[][]): SubtitleSegment[] {
  return lines.map((line) => ({
    text: line.map((c) => c.text).join(" "),
    start_ms: line[0].start_ms,
    end_ms: line[line.length - 1].end_ms,
  }));
}

/** BR-2: a segment shorter than 700ms is merged into the next one (or the
 * previous one, if it's the last segment) so it never flickers on screen. */
function mergeShortSegments(segments: SubtitleSegment[]): SubtitleSegment[] {
  if (segments.length <= 1) return segments;
  const result: SubtitleSegment[] = [];
  let i = 0;
  while (i < segments.length) {
    const seg = segments[i];
    const duration = seg.end_ms - seg.start_ms;
    const isLast = i === segments.length - 1;

    if (duration < MIN_SEGMENT_DURATION_MS && !isLast) {
      const next = segments[i + 1];
      result.push({
        text: `${seg.text} ${next.text}`,
        start_ms: seg.start_ms,
        end_ms: next.end_ms,
      });
      i += 2;
      continue;
    }

    if (duration < MIN_SEGMENT_DURATION_MS && isLast && result.length > 0) {
      const prev = result.pop() as SubtitleSegment;
      result.push({
        text: `${prev.text} ${seg.text}`,
        start_ms: prev.start_ms,
        end_ms: seg.end_ms,
      });
      i += 1;
      continue;
    }

    result.push(seg);
    i += 1;
  }
  return result;
}

/**
 * Segment word timestamps into subtitle display segments per BR-1/2/4.
 *
 * Empty input returns an empty array (caller decides whether that means
 * "no subtitle" — see BR-3, handled by the Subtitle component, not here).
 */
export function segmentTimestamps(words: WordTimestamp[]): SubtitleSegment[] {
  if (words.length === 0) return [];
  const clusters = buildClusters(words);
  const lines = packIntoLines(clusters);
  const segments = linesToSegments(lines);
  // Repeat merge passes until stable — a merge can create a new short
  // segment at a boundary that itself needs merging.
  let merged = mergeShortSegments(segments);
  for (let pass = 0; pass < segments.length; pass += 1) {
    const next = mergeShortSegments(merged);
    if (next.length === merged.length) break;
    merged = next;
  }
  return merged;
}

/** Returns the segment active at `timeMs` (relative to scene start), or null. */
export function activeSegmentAt(
  segments: SubtitleSegment[],
  timeMs: number
): SubtitleSegment | null {
  return segments.find((s) => timeMs >= s.start_ms && timeMs < s.end_ms) ?? null;
}
