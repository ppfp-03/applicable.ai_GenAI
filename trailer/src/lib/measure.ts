import { fitText, measureText } from "@remotion/layout-utils";
import { FONT } from "../brand/tokens";

// Headline sizing is computed, never eyeballed. Only valid inside <FontGate> (fonts loaded):
// validateFontIsLoaded makes a fallback-font measurement throw instead of silently lying.

export type TextStyle = { size: number; weight: number; track?: number; family?: string };

/** Width in px of one line of text. */
export const lineWidth = (text: string, s: TextStyle) =>
  measureText({
    text,
    fontFamily: s.family ?? FONT.app,
    fontSize: s.size,
    fontWeight: String(s.weight),
    letterSpacing: `${s.track ?? 0}em`,
    validateFontIsLoaded: true,
  }).width;

/**
 * The largest size <= s.size at which every line fits in maxWidth. Lines are authored (intentional
 * breaks), so a headline can only shrink, never re-wrap.
 */
export const fitLines = (lines: string[], maxWidth: number, s: TextStyle) => {
  let size = s.size;
  for (const line of lines) {
    const fit = fitText({
      text: line,
      withinWidth: maxWidth,
      fontFamily: s.family ?? FONT.app,
      fontWeight: String(s.weight),
      letterSpacing: `${s.track ?? 0}em`,
      validateFontIsLoaded: true,
    }).fontSize;
    size = Math.min(size, fit);
  }
  return Math.floor(size * 100) / 100;
};
