/**
 * Subtitle segmentation — groups word-level timestamps (from VoiceSpec.audio.timestamps,
 * docs/specs/scene-json-schema.md §3.4) into display segments for the `line` subtitle style.
 *
 * Segments are generated at props-preparation time (never persisted in Scene JSON — §3.4).
 *
 * Business rules (task 2-5):
 *   BR-1: never split a number+unit cluster ("92,5 phần trăm" stays one segment).
 *   BR-2: a segment with total display duration < 700ms merges into the next segment.
 *   BR-3: handled at the component layer (Subtitle.tsx), not here.
 *   BR-4: a single token longer than the line limit is allowed to overflow rather than
 *         being cut mid-word.
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

/** A token is a "number head" if it starts with a digit — its following token (the unit)
 * must not be split into a different segment (BR-1). This is a best-effort heuristic:
 * the TTS word-timestamp stream carries no explicit semantic-cluster annotation, so a
 * digit-leading token is treated as binding to the single token that immediately follows it. */
function isNumberHead(token: string): boolean {
  return /^[0-9][0-9.,]*$/.test(token);
}

/** Punctuation that makes a good segment boundary (prefer breaking here over mid-clause). */
function endsWithPunctuation(token: string): boolean {
  return /[.,!?;:…]$/.test(token);
}

interface RawGroup {
  words: WordTimestamp[];
}

/**
 * Pure function: word timestamps -> subtitle segments.
 * Concatenation of all segment texts (joined by a single space) always equals the
 * original word sequence — no characters are ever lost (property test, task 2-5 Step 5).
 */
export function segmentTimestamps(words: WordTimestamp[]): SubtitleSegment[] {
  if (words.length === 0) return [];

  // Pass 1: greedy line-length grouping that respects word boundaries (never cut mid-word,
  // BR-4), prefers punctuation boundaries, and never splits a number+unit cluster (BR-1).
  const groups: RawGroup[] = [];
  let current: WordTimestamp[] = [];
  let currentLen = 0;

  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const isBoundToNext = isNumberHead(w.word) && i + 1 < words.length;
    const clusterEnd = isBoundToNext ? i + 1 : i;
    const cluster = words.slice(i, clusterEnd + 1);
    const clusterText = cluster.map((c) => c.word).join(' ');
    const addedLen = currentLen === 0 ? clusterText.length : currentLen + 1 + clusterText.length;

    // BR-4: never cut mid-word/mid-cluster. If the line is non-empty and adding this
    // cluster would overflow, close the current line first — even if the cluster itself
    // is longer than the limit (soft overflow, allowed only when it's the sole content).
    if (currentLen > 0 && addedLen > MAX_CHARS_PER_LINE) {
      groups.push({words: current});
      current = [];
      currentLen = 0;
    }

    current.push(...cluster);
    currentLen = current.map((c) => c.word).join(' ').length;
    i = clusterEnd;

    const lastWord = cluster[cluster.length - 1];
    const atLineLimit = currentLen >= MAX_CHARS_PER_LINE;
    const atPunctuationBoundary = endsWithPunctuation(lastWord.word);

    if (atLineLimit || (atPunctuationBoundary && currentLen > MAX_CHARS_PER_LINE * 0.4)) {
      groups.push({words: current});
      current = [];
      currentLen = 0;
    }
  }
  if (current.length > 0) groups.push({words: current});

  // Pass 2: merge any segment whose display duration is below the minimum (BR-2).
  // A short segment folds forward into the next segment; if it's the last segment
  // with nothing after it, it folds backward into the previous one instead.
  const finalGroups: RawGroup[] = [];
  for (let i = 0; i < groups.length; i++) {
    const g = groups[i];
    const duration = g.words[g.words.length - 1].end_ms - g.words[0].start_ms;
    const isLast = i === groups.length - 1;
    if (duration < MIN_SEGMENT_DURATION_MS && !isLast) {
      groups[i + 1] = {words: [...g.words, ...groups[i + 1].words]};
      continue;
    }
    if (duration < MIN_SEGMENT_DURATION_MS && isLast && finalGroups.length > 0) {
      const prev = finalGroups.pop()!;
      finalGroups.push({words: [...prev.words, ...g.words]});
      continue;
    }
    finalGroups.push(g);
  }

  return finalGroups.map((g) => ({
    text: g.words.map((w) => w.word).join(' '),
    start_ms: g.words[0].start_ms,
    end_ms: g.words[g.words.length - 1].end_ms,
  }));
}
