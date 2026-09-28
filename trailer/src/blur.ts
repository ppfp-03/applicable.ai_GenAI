import { ACT, ACT_KEYS, CUE, TOTAL } from "./timeline";

// Temporal motion blur, the way a film camera makes it: an output frame is the average of n
// renders spread across the shutter interval, centred on the frame's time. n comes from how fast
// things move on screen in that frame (scripts/measure-speed.py runs optical flow on the sharp
// render), so fast moves smear instead of stamping copies and still frames render once.
//
// The averaging happens outside Chromium (scripts/accumulate.py, float32, quantized once).

export const SHUTTER = 216; // degrees; scripts/measure-speed.py reads the same value from here via cues

// Hard state changes. A shutter must never straddle one, or the frame would show two states at
// once (two acts, or "99 applicants" and "100+ applicants" double-exposed on the downbeat).
export const SEAMS = [...ACT_KEYS.map((k) => ACT[k].from), CUE.hundred, TOTAL].sort((a, b) => a - b);

/** The n sub-frame times that make up output frame f, clamped between the seams around it. */
export const sampleTimes = (f: number, n: number): number[] => {
  if (n <= 1) return [f];
  const span = SHUTTER / 360;
  const lo = Math.max(...SEAMS.filter((s) => s <= f));
  const hi = Math.min(...SEAMS.filter((s) => s > f)) - 1e-3;
  // the open shutter, cut short where it would cross a seam; samples stay evenly spaced inside it
  const a = Math.max(lo, f - span / 2);
  const b = Math.min(hi, f + span / 2);
  return Array.from({ length: n }, (_, i) => a + (b - a) * ((i + 0.5) / n));
};

export type SubFrame = { f: number; t: number };

/** Every sub-frame of the blurred master, in order, for per-frame sample counts `groups`. */
export const subframes = (groups: number[]): SubFrame[] => {
  const out: SubFrame[] = [];
  for (let f = 0; f < TOTAL; f++) for (const t of sampleTimes(f, groups[f] ?? 1)) out.push({ f, t });
  return out;
};
