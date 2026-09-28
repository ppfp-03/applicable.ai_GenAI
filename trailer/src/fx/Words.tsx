import React from "react";
import { E, prog } from "../lib/anim";

/**
 * Word-by-word reveal: each word rises a fraction of an em, sharpens from a blur and fades in.
 * The rhythm lives in the stagger, not in per-letter effects. `out` starts a quick exit.
 */
export const Words: React.FC<{
  text: string;
  f: number; // local frame
  start: number;
  stagger?: number;
  dur?: number;
  rise?: number; // em
  blur?: number; // px
  out?: number;
  outDur?: number;
  style?: React.CSSProperties;
  wordStyle?: (i: number, word: string) => React.CSSProperties;
}> = ({ text, f, start, stagger = 5, dur = 24, rise = 0.28, blur = 12, out, outDur = 14, style, wordStyle }) => {
  const words = text.split(" ");
  return (
    <span style={{ display: "inline-block", whiteSpace: "pre", ...style }}>
      {words.map((w, i) => {
        const p = prog(f, start + i * stagger, start + i * stagger + dur, E.out);
        const q = out === undefined ? 0 : prog(f, out + i * 2, out + i * 2 + outDur, E.in);
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${((1 - p) * rise - q * rise * 0.5).toFixed(4)}em)`,
              filter: (1 - p) * blur + q * blur > 0.05 ? `blur(${((1 - p) * blur + q * blur).toFixed(2)}px)` : undefined,
              opacity: p * (1 - q),
              ...(wordStyle ? wordStyle(i, w) : {}),
            }}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </span>
        );
      })}
    </span>
  );
};
