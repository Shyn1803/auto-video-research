/**
 * textDiff — parses the unified-diff string the backend already computes
 * (app/services/versioning_service.py `compare()`, difflib.unified_diff) for
 * outline/script steps, into structured lines a component can render.
 *
 * BR-4 (a11y): additions/removals must be marked with a prefix (+/-) AND
 * color — never color alone. This module doesn't decide color (that's the
 * component's job via CSS classes), but it does preserve the literal +/-
 * prefix character in `text` so a consumer can never accidentally drop it.
 */

export type DiffLineType = "add" | "remove" | "context" | "hunk";

export interface DiffLine {
  type: DiffLineType;
  /** Raw line, prefix (+/-/space) included verbatim. */
  text: string;
}

export function parseUnifiedDiff(diff: string | null | undefined): DiffLine[] {
  if (!diff) return [];
  return diff.split("\n").map((line): DiffLine => {
    if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
      return { type: "hunk", text: line };
    }
    if (line.startsWith("+")) {
      return { type: "add", text: line };
    }
    if (line.startsWith("-")) {
      return { type: "remove", text: line };
    }
    return { type: "context", text: line };
  });
}

export interface SideBySideDiff {
  left: DiffLine[];
  right: DiffLine[];
}

/** Splits parsed diff lines into old(left)/new(right) columns: removed
 * lines appear only on the left, added only on the right, context lines
 * mirrored on both — an approximation of a true side-by-side diff built
 * from the unified-diff text the backend already returns (BR: "màn diff
 * side-by-side text"). */
export function toSideBySide(lines: DiffLine[]): SideBySideDiff {
  const left: DiffLine[] = [];
  const right: DiffLine[] = [];
  for (const line of lines) {
    if (line.type === "hunk") continue;
    if (line.type === "remove") {
      left.push(line);
    } else if (line.type === "add") {
      right.push(line);
    } else {
      left.push(line);
      right.push(line);
    }
  }
  return { left, right };
}
