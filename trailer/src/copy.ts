import { CUE } from "./timeline";

// Every on-screen line of the film (approved copy only), with the frame each line starts and the
// stagger between its words. The acts render from here and scripts/export-cues.ts exports the
// per-word arrival frames, so the soundtrack's word accents land with the words.

export type Line = { text: string; start: number; stagger: number };

export const COPY = {
  foundIt: { text: "You found it.", start: CUE.foundIt, stagger: 4 },
  everyone: { text: "So did everyone else.", start: CUE.everyone, stagger: 5 },
  finding: { text: "Finding opportunities", start: CUE.line1, stagger: 6 },
  notEnough: { text: "isn’t enough.", start: CUE.line1 + 12, stagger: 6 },
  timing: { text: "Timing is the edge.", start: CUE.line2, stagger: 7 },
  seeWhat: { text: "See what matters", start: CUE.headline4, stagger: 5 },
  whileIt: { text: "while it still matters.", start: CUE.headline4 + 16, stagger: 5 },
  knowWhere: { text: "Know where to move first.", start: CUE.headline5, stagger: 5 },
  yourEdge: { text: "Your competitive edge starts with", start: CUE.headline6, stagger: 4 },
  knowing: { text: "knowing where to move first.", start: CUE.headline6 + 22, stagger: 4 },
} satisfies Record<string, Line>;

/** Frames at which each word of a line visibly arrives (its reveal is ~60% done). */
export const wordFrames = (l: Line) => l.text.split(" ").map((_, i) => l.start + i * l.stagger + 5);
