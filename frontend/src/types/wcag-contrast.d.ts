/**
 * `wcag-contrast` (npm) ships no bundled TypeScript types — this is a minimal
 * ambient declaration for the two functions this codebase uses.
 * https://github.com/tmcw/wcag-contrast
 */
declare module "wcag-contrast" {
  /** Contrast ratio (1–21) between two hex colors, e.g. hex("#000", "#fff") === 21 */
  export function hex(a: string, b: string): number;
  /** Textual WCAG score for a numeric ratio: "AAA" | "AA" | "AA18" | "-" */
  export function score(contrast: number): string;
}
