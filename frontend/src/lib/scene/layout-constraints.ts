/**
 * Client-side mirror of the layout element-constraint table
 * (docs/specs/scene-json-schema.md §2 "Layout catalog") — used for the BR-1
 * dry-run check before committing a `layout`/`layout_override` change.
 *
 * No backend dry-run endpoint exists yet: the real Constraint Resolver
 * (layout-engine.md §6, task 4-6 "Semantic Storyboard + Layout Engine core")
 * is still `not-started` in sprint-status.yaml. Per task 5-2's own Execution
 * Step 4 note ("...else client-side constraint check reusing the Layout
 * Engine's constraint resolver contract"), this module re-derives the same
 * table the backend spec documents, scoped to what TextControl/ImageElement
 * counts can express. When 4-6 ships a real `/api/scenes/{id}/dry-run`
 * endpoint, LayoutDryRunDialog should call that instead of this table —
 * tracked as a follow-up in this task's retrospective.
 */

export interface LayoutElementConstraint {
  minTexts: number;
  maxTexts: number;
  minImages: number;
  maxImages: number;
}

/** scene-json-schema.md §2 table, text/image bounds only (specialized
 * element kinds — number/chart/table/list/quote_block/code — are out of
 * scope for this text/image dry-run; bounds below are set generously so an
 * unsupported target layout never produces a false-positive violation). */
export const LAYOUT_CONSTRAINTS: Record<string, LayoutElementConstraint> = {
  Hero: { minTexts: 1, maxTexts: 2, minImages: 0, maxImages: 1 },
  TextFocus: { minTexts: 1, maxTexts: 3, minImages: 0, maxImages: 0 },
  MediaFull: { minTexts: 0, maxTexts: 2, minImages: 1, maxImages: 1 },
  MediaText: { minTexts: 1, maxTexts: 3, minImages: 1, maxImages: 1 },
  Comparison: { minTexts: 0, maxTexts: 3, minImages: 0, maxImages: 2 },
  BigNumber: { minTexts: 0, maxTexts: 1, minImages: 0, maxImages: 1 },
  Chart: { minTexts: 0, maxTexts: 2, minImages: 0, maxImages: 0 },
  VersusTable: { minTexts: 0, maxTexts: 1, minImages: 0, maxImages: 0 },
  List: { minTexts: 0, maxTexts: 1, minImages: 0, maxImages: 0 },
  Quote: { minTexts: 0, maxTexts: 0, minImages: 0, maxImages: 1 },
  Code: { minTexts: 0, maxTexts: 1, minImages: 0, maxImages: 0 },
};

export interface DryRunTextLike {
  id: string;
  content: string;
}

export interface LayoutDryRunResult {
  ok: boolean;
  /** ids of texts that would be dropped, in original order — always the
   * tail of the list past `maxTexts` (deterministic, matches AC-2's
   * "chữ 't3' sẽ bị bỏ" when t3 is the 3rd of 3 texts moving to a 2-max layout). */
  droppedTextIds: string[];
  /** short excerpt of each dropped text's content, for the dialog message */
  droppedTextExcerpts: { id: string; excerpt: string }[];
  imagesExceed: boolean;
  imagesCount: number;
  imagesMax: number;
}

/** Pure function — no I/O, safe to unit test without a backend. */
export function checkLayoutChange(
  texts: DryRunTextLike[],
  imagesCount: number,
  targetLayout: string,
): LayoutDryRunResult {
  const constraint = LAYOUT_CONSTRAINTS[targetLayout];

  // Unknown target (e.g. a class this dry-run doesn't model) — don't block.
  if (!constraint) {
    return {
      ok: true,
      droppedTextIds: [],
      droppedTextExcerpts: [],
      imagesExceed: false,
      imagesCount,
      imagesMax: Infinity,
    };
  }

  const dropped = texts.slice(constraint.maxTexts);
  const imagesExceed = imagesCount > constraint.maxImages;

  return {
    ok: dropped.length === 0 && !imagesExceed,
    droppedTextIds: dropped.map((t) => t.id),
    droppedTextExcerpts: dropped.map((t) => ({
      id: t.id,
      excerpt: t.content.slice(0, 24),
    })),
    imagesExceed,
    imagesCount,
    imagesMax: constraint.maxImages,
  };
}
