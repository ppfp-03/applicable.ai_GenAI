// Exports every sync point of the film to out/cues.json for scripts/soundtrack.py.
//
// Nothing here is typed in by hand: beats come from src/timeline.ts, words from src/copy.ts, and
// motion events are measured from the same functions the picture uses - a spring's sound goes on
// the frame the spring first reaches its target, a whoosh's apex on the frame of peak velocity,
// an applicant's click on the exact (fractional) frame its seat fills, a posting's tick on the
// frame it slides out from behind the now edge.
//
// Run: npx tsx scripts/export-cues.ts
import { mkdirSync, writeFileSync } from "node:fs";
import { ACT, BAR, BEAT, BPM, CUE, FPS, TOTAL } from "../src/timeline";
import { COPY, wordFrames } from "../src/copy";
import { E, peakFrame, SPR, springHit } from "../src/lib/anim";
import { AGES, arrivalFrame, CURSOR, HUNDRED, PUNCH, SPILL } from "../src/acts/act1-data";
import { dayAt, LAYERS, MARKET, NOW_X } from "../src/jobboard/market";
import { RUSH, RUSH_EASE } from "../src/acts/Act2Problem";
import { R3, WAVE_EASE } from "../src/acts/Act3Reveal";
import { EDGE_SLIDE, PUSH4 } from "../src/acts/Act4Freshness";
import { FRESH, LANES, NOW4, STALE } from "../src/acts/act4-data";
import { T5 } from "../src/acts/act5-data";
import { R6 } from "../src/acts/Act6Lockup";
import { SHUTTER } from "../src/blur";

const r2 = (x: number) => Math.round(x * 100) / 100;

/** Frame at which the world clock reaches `day` (bisection on the monotonic clock). */
const frameOfDay = (day: number) => {
  let lo = CUE.pullBack;
  let hi = ACT.reveal.from + 60;
  if (dayAt(hi) < day) return null;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (dayAt(mid) < day) lo = mid;
    else hi = mid;
  }
  return hi;
};

// postings sliding out from behind the now edge during the market act (front lanes, audible range)
const births = MARKET.filter((p) => p.layer === 0 && !p.hero)
  .map((p) => ({ f: frameOfDay(p.born), lane: p.lane }))
  .filter((b): b is { f: number; lane: number } => b.f !== null && b.f >= CUE.voidIn && b.f < ACT.reveal.from)
  .map((b) => ({ f: r2(b.f), pan: r2(((b.lane / (LAYERS[0].lanes - 1)) * 2 - 1) * 0.6) }))
  .sort((a, b) => a.f - b.f);

const words = Object.fromEntries(Object.entries(COPY).map(([k, l]) => [k, wordFrames(l)]));

const landHit = springHit(SPR.land, 1);
const cues = {
  fps: FPS,
  total: TOTAL,
  bpm: BPM,
  beat: BEAT,
  bar: BAR,
  shutter: SHUTTER,
  acts: ACT,
  cue: CUE,
  words,
  act1: {
    ageTicks: AGES.slice(1).map((a) => a.f),
    applicants: Array.from({ length: 99 }, (_, i) => r2(arrivalFrame(i + 1))),
    hundred: HUNDRED,
    spill: Array.from({ length: SPILL }, (_, k) => r2(HUNDRED + k * 1.6)),
    punchIn: r2(peakFrame(PUNCH.at, PUNCH.at + PUNCH.in, E.out)),
    punchOut: r2(peakFrame(PUNCH.holdTo, PUNCH.outTo, E.cam)),
    cursor: r2(peakFrame(CURSOR.from, CURSOR.to, E.cam)),
    click: CUE.click,
    pullBack: r2(peakFrame(CUE.pullBack, CUE.pullBack + 44, E.in)),
  },
  act2: {
    births,
    edgeGlow: CUE.edgeGlow,
    rushPeak: r2(peakFrame(RUSH.from, RUSH.to, RUSH_EASE)),
  },
  act3: {
    drop: CUE.drop1,
    wavePeak: r2(peakFrame(R3.wave.from, R3.wave.to, WAVE_EASE)),
    collapsePeak: r2(peakFrame(R3.collapse.from, R3.collapse.to, E.inOut)),
    tileLand: r2(R3.widen + springHit(SPR.pop, 1)),
    aIn: r2(CUE.aIn + springHit(SPR.snap, 1)),
    wordmark: r2(peakFrame(CUE.wordmark, CUE.wordmark + 36, E.out)),
    lockShift: r2(peakFrame(R3.lockShift.from, R3.lockShift.to, E.inOut)),
    tuck: r2(peakFrame(R3.tuck.from, R3.tuck.to, E.in)),
    unfoldPeak: r2(peakFrame(R3.unfoldH.from, R3.unfoldH.to, E.inOut)),
  },
  act4: {
    edgeSlide: r2(peakFrame(EDGE_SLIDE.from, EDGE_SLIDE.to, E.cam)),
    // the field unfolds out of the edge: each old role arrives at its age (E.out: arrival ~ start + 12)
    unfold: STALE.map((r) => ({ f: r2(ACT.fresh.from + 6 + (1 - r.days / 18) * 14 + 12), days: r.days })),
    recede: STALE.filter((r) => r.recede !== undefined).map((r) => ({ f: r.recede!, days: r.days })),
    emerge: FRESH.map((r) => ({ f: r.emerge!, land: r2(r.emerge! + landHit), lane: r.lane, y: LANES[r.lane] })),
    push: r2(peakFrame(PUSH4.from, PUSH4.to, E.push)),
    edgeX: NOW4,
  },
  act5: {
    emerge: T5.emerge,
    emergeLand: r2(T5.emerge + landHit),
    checks: T5.checks,
    listIn: T5.listIn,
    lift: T5.lift,
    flyPeak: r2(peakFrame(T5.fly.from, T5.fly.to, E.inOut)),
    land: CUE.land,
    shiftLands: [0, 1, 2].map((i) => r2(T5.shift + i * 3 + landHit)),
    ring: T5.ring,
  },
  act6: {
    rest: r2(peakFrame(R6.rest.from, R6.rest.to, E.inOut)),
    center: r2(peakFrame(R6.center.from, R6.center.to, E.inOut)),
    morphPeak: r2(peakFrame(R6.morph.from, R6.morph.to, E.inOut)),
    tileLand: R6.morph.to,
    aIn: r2(CUE.aIn6 + springHit(SPR.snap, 1)),
    wordmark: r2(peakFrame(R6.word.from, R6.word.to, E.out)),
    lockup: CUE.lockup,
  },
  nowX: NOW_X,
};

mkdirSync("out", { recursive: true });
writeFileSync("out/cues.json", JSON.stringify(cues, null, 1));
console.log(
  `wrote out/cues.json: ${cues.act1.applicants.length} applicant clicks, ${births.length} market births, ` +
    `${Object.values(words).flat().length} word accents; drop1 f${CUE.drop1}, land f${CUE.land}, lockup f${CUE.lockup}`,
);
