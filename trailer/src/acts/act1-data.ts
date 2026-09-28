import { interpolate } from "remotion";
import { CUE } from "../timeline";

// ACT 1 data: one fictional posting on a fictional generic job board, aging while the crowd
// arrives. The applicant counts belong to that board's world; Applicable.ai never claims them.

// The posting's age label steps on the beat (the clock).
export const AGES: { f: number; label: string }[] = [
  { f: 0, label: "Just posted" },
  { f: 30, label: "20 minutes ago" },
  { f: 60, label: "1 hour ago" },
  { f: 90, label: "6 hours ago" },
  { f: 120, label: "1 day ago" },
  { f: 150, label: "2 days ago" },
  { f: CUE.hundred, label: "3 days ago" },
];

export const ageAt = (f: number) => {
  let i = 0;
  for (let k = 0; k < AGES.length; k++) if (f >= AGES[k].f) i = k;
  return i;
};

// Applicants: 12 -> 34 -> 68 -> (a held breath at 99) -> 100+ on the downbeat. The count rate keeps
// rising so the clicks of arriving applicants thicken into a crowd.
const CF = [0, 14, 60, 100, 140, 172];
const CV = [0, 1, 12, 34, 68, 99];
export const HUNDRED = CUE.hundred;

export const countAt = (f: number) =>
  f >= HUNDRED ? 100 : Math.floor(interpolate(f, CF, CV, { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));

/** Exact (fractional) frame at which applicant n (1..99) arrives. */
export const arrivalFrame = (n: number) => {
  for (let i = 1; i < CV.length; i++) {
    if (n <= CV[i]) {
      const t = (n - CV[i - 1]) / (CV[i] - CV[i - 1]);
      return CF[i - 1] + t * (CF[i] - CF[i - 1]);
    }
  }
  return HUNDRED;
};

export const METER = { cols: 25, rows: 4, dot: 14, gap: 8 };
// Applicants that no longer fit: they spill out of the meter on the 100+ hit.
export const SPILL = 14;

// Camera keys (page coordinates; see acts/Act1TooLate.tsx).
// the punch-in waits two frames so the 100+ downbeat itself is seen sharp
export const PUNCH = { at: HUNDRED + 2, in: 10, holdTo: HUNDRED + 22, outTo: HUNDRED + 54 };
export const CURSOR = { from: HUNDRED + 18, to: CUE.click - 2 };
