// Single source of truth for time. The picture reads these frames; scripts/export-cues.ts exports
// them (plus the motion events derived from them) to out/cues.json for the soundtrack generator.
//
// 60 fps, 120 BPM: 1 beat = 30 frames, 1 bar = 120 frames. The film is 15 bars = 1800 frames.

export const FPS = 60;
export const W = 1920;
export const H = 1080;
export const BPM = 120;
export const BEAT = (60 / BPM) * FPS; // 30 frames
export const BAR = BEAT * 4; // 120 frames

/** Absolute frame of bar (1-indexed), beat offset and 16th offset. */
export const b = (bar: number, beat = 0, sixteenth = 0) =>
  Math.round(((bar - 1) * 4 + beat) * BEAT + sixteenth * (BEAT / 4));

export const TOTAL = 1800; // exactly 30.000 s

// Acts, in absolute frames. Sub-frame motion-blur samples never cross these seams.
export const ACT = {
  tooLate: { from: 0, dur: 360 }, // 0:00 a posting ages while the crowd arrives
  problem: { from: 360, dur: 240 }, // 0:06 the market, drifting away from now
  reveal: { from: 600, dur: 240 }, // 0:10 the now edge ignites into Applicable.ai
  fresh: { from: 840, dur: 360 }, // 0:14 time made visible: old recedes, fresh emerges
  actFirst: { from: 1200, dur: 300 }, // 0:20 a strong new role rises to #1
  edge: { from: 1500, dur: 300 }, // 0:25 resolution and lockup
} as const;

export type ActKey = keyof typeof ACT;
export const ACT_KEYS = Object.keys(ACT) as ActKey[];

// Picture/music cues (absolute frames). Everything that makes a sound or lands on the grid is here
// or is derived from here by the act modules.
export const CUE = {
  // ACT 1 - TOO LATE
  hundred: b(2, 2), // "100+ applicants" resolves (f180)
  click: b(2, 3) + 10, // you arrive and save it (f220)
  foundIt: b(2, 3) + 16, // "You found it." (f226)
  everyone: b(3, 0) + 8, // "So did everyone else." (f248)
  pullBack: b(3, 2) + 12, // the posting starts to age away from now (f312)
  textOut: b(3, 2) + 12, // the lines leave before the lights go down (f312)
  voidIn: b(3, 2) + 26, // lights dim into the market (f326)
  // ACT 2 - THE REAL PROBLEM
  line1: b(4, 1), // "Finding opportunities isn't enough." (f390)
  line1Out: b(4, 3) + 20, // (f470)
  line2: b(5, 0) + 6, // "Timing is the edge." (f486)
  edgeGlow: b(5, 0) + 27, // the edge lights up as the word "edge" lands
  line2Out: b(5, 2) + 16, // (f556)
  rush: b(5, 2) + 18, // the camera rushes the now edge (f558)
  // ACT 3 - APPLICABLE.AI
  drop1: b(6, 0), // ignition (f600)
  waveEnd: b(6, 1) + 22, // (f652)
  aIn: b(6, 2) + 24,
  wordmark: b(6, 3) + 6,
  unfold: b(7, 2) + 20, // the tile becomes the product's now line again (f800)
  // ACT 4 - FIND WHAT'S FRESH
  fieldIn: b(8, 0), // the edge slides to its place and the field unfolds out of it (f840)
  headline4: b(8, 1), // "See what matters while it still matters." (f870)
  recede: [b(8, 2), b(8, 3), b(9, 0), b(9, 1)] as const, // older roles sink back, one per beat
  emerge: [b(9, 2), b(9, 3) + 15, b(10, 1)] as const, // fresh roles born at the edge
  headline4Out: b(10, 3) + 10,
  push4: b(10, 3), // the camera closes on the edge (f1170)
  // ACT 5 - ACT FIRST
  hero: b(11, 0), // the strong new role appears (f1200)
  check1: b(11, 1) + 6,
  check2: b(11, 2) + 6,
  lift: b(11, 3) + 6,
  land: b(12, 0), // lands at #1: drop 2 (f1320)
  headline5: b(12, 0) + 8,
  // ACT 6 - COMPETITIVE EDGE
  resolve: b(13, 2), // (f1500)
  headline6: b(13, 3) + 12, // (f1542)
  merge: b(14, 2),
  aIn6: b(14, 3),
  lockup: b(15, 0), // final lockup (f1680)
};
