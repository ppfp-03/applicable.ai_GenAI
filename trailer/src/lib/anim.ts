import { Easing, interpolate } from "remotion";

// The film's motion vocabulary. Every timeline-critical value in the picture is a pure function of
// the (possibly fractional) frame, so the motion-blur path can sample any sub-frame time and the cue
// exporter can find landings and velocity peaks with the same functions the picture uses.

export type Ease = (t: number) => number;

// Easings are named after how they feel, not the maths.
export const E = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // expo-out: arrivals, reveals
  outSoft: Easing.bezier(0.22, 1, 0.36, 1), // quint-out: gentle settles
  in: Easing.bezier(0.7, 0, 0.84, 0), // expo-in: departures, collapses
  inOut: Easing.bezier(0.87, 0, 0.13, 1), // expo-in-out: whips, match moves
  smooth: Easing.bezier(0.65, 0, 0.35, 1), // cubic-in-out: drifts
  swift: Easing.bezier(0.4, 0, 0.2, 1), // UI state changes
  cam: Easing.bezier(0.45, 0.05, 0.1, 1), // house camera: eased start, early peak, long settle
  push: Easing.bezier(0.55, 0, 0.9, 0.4), // accelerating push that is still moving at its end
  linear: (t: number) => t,
} satisfies Record<string, Ease>;

/** Clamped tween of a value between two frames. */
export const tw = (f: number, from: number, to: number, a: number, b: number, ease: Ease = E.out) =>
  interpolate(f, [from, to], [a, b], {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** 0..1 progress between two frames. */
export const prog = (f: number, from: number, to: number, ease: Ease = E.out) => tw(f, from, to, 0, 1, ease);

export const mix = (a: number, b: number, t: number) => a + (b - a) * t;
export const clamp = (x: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));

/**
 * Hit envelope for impacts and ticks: rises to 1 `attack` frames after t = 0 (so the picture
 * peaks with its sound), then decays exponentially.
 */
export const hitPulse = (t: number, attack = 2, tau = 6) =>
  t <= 0 || t > attack + 7 * tau
    ? 0
    : t < attack
      ? Math.sin((t / attack) * (Math.PI / 2))
      : Math.exp(-(t - attack) / tau);

// ---------------------------------------------------------------------------------------------
// Springs, closed form. Remotion's spring() steps a simulation per frame; this is the analytic
// damped oscillator, so it is exact at fractional frames (sub-frame motion blur) and cheap to scan
// (scripts/export-cues.ts finds the frame each spring lands on to place its sound).
// ---------------------------------------------------------------------------------------------
export type Spring = { stiffness: number; damping: number; mass: number };

export const SPR = {
  snap: { stiffness: 320, damping: 22, mass: 0.8 }, // locks in with a small overshoot
  pop: { stiffness: 240, damping: 13, mass: 0.7 }, // playful overshoot
  soft: { stiffness: 140, damping: 24, mass: 1 }, // weighty, no overshoot
  heavy: { stiffness: 120, damping: 20, mass: 1.6 }, // big object with inertia
  land: { stiffness: 260, damping: 17, mass: 1 }, // a card landing: one visible rebound
} satisfies Record<string, Spring>;

/** Position 0 -> 1 of a spring released from rest `t` frames ago (60 fps). */
export const springAt = (t: number, s: Spring, fps = 60): number => {
  if (t <= 0) return 0;
  const sec = t / fps;
  const w0 = Math.sqrt(s.stiffness / s.mass);
  const zeta = s.damping / (2 * Math.sqrt(s.stiffness * s.mass));
  if (zeta < 1) {
    const wd = w0 * Math.sqrt(1 - zeta * zeta);
    const env = Math.exp(-zeta * w0 * sec);
    return 1 - env * (Math.cos(wd * sec) + ((zeta * w0) / wd) * Math.sin(wd * sec));
  }
  if (zeta === 1) return 1 - Math.exp(-w0 * sec) * (1 + w0 * sec);
  // overdamped: displacement d(t) = c1 e^(r1 t) + c2 e^(r2 t) with d(0) = -1, d'(0) = 0
  const r1 = -w0 * (zeta - Math.sqrt(zeta * zeta - 1));
  const r2 = -w0 * (zeta + Math.sqrt(zeta * zeta - 1));
  const c1 = -r2 / (r2 - r1);
  const c2 = r1 / (r2 - r1);
  return 1 + c1 * Math.exp(r1 * sec) + c2 * Math.exp(r2 * sec);
};

/** Spring value between a and b, released at frame `start`. */
export const spr = (f: number, start: number, a: number, b: number, s: Spring = SPR.snap) =>
  mix(a, b, springAt(f - start, s));

/** First frame (relative to release) at which the spring first reaches `thr` of its travel. */
export const springHit = (s: Spring, thr = 1, fps = 60) => {
  for (let i = 0; i < 600; i++) if (springAt(i / 4, s, fps) >= thr) return i / 4;
  return 150;
};

// ---------------------------------------------------------------------------------------------
// Deterministic randomness.
// ---------------------------------------------------------------------------------------------
export const rand = (seed: number | string) => {
  let h = typeof seed === "number" ? Math.imul(seed | 0, 2654435761) ^ Math.floor(seed * 1e6) : 0x9e3779b9;
  if (typeof seed === "string") for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 2654435761);
  h ^= h >>> 16;
  h = Math.imul(h, 2246822507);
  h ^= h >>> 13;
  h = Math.imul(h, 3266489909);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
};

/** Frame of peak velocity of a tween running from frame a to b with the given easing. */
export const peakFrame = (a: number, b: number, ease: Ease) => {
  let best = a;
  let bestV = -1;
  const n = 600;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    const v = ease(Math.min(1, t + 1 / n)) - ease(t);
    if (v > bestV) {
      bestV = v;
      best = a + (t + 0.5 / n) * (b - a);
    }
  }
  return best;
};
