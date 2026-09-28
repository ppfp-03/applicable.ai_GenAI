import { Match, ROW } from "../product/ui";
import { CUE } from "../timeline";

// ACT 5 data. The three roles already at the top of "Your top matches" (the app's own demo roles)
// and the strong new role that Applicable.ai has just seen. It outranks them on fit, preferences
// and deadline as well as freshness: the bar shows all four factor families, freshness is one.
// Scores are illustrative.

export const LIST = { x: 130, top: 440, pitch: 128, headerY: 382 };
// after the landing the camera frames the list (world focus + scale)
export const LIST_CAM = { x: 130 + ROW.w / 2, y: 628, s: 1.13 };
export const slotY = (i: number) => LIST.top + i * LIST.pitch;

export const EXISTING: Match[] = [
  {
    mono: "RP",
    title: "Product Analyst Intern",
    place: "Replai · London",
    why: "Strongest skills match",
    tag: "First seen 6 days ago",
    score: 87,
    fx: { profile: 0.35, preference: 0.23, deadline: 0.19, freshness: 0.1 },
  },
  {
    mono: "BC",
    title: "Strategy Intern",
    place: "Bolton Consulting Group · London",
    why: "Best fit with preferences",
    tag: "First seen 9 days ago",
    score: 83,
    fx: { profile: 0.31, preference: 0.25, deadline: 0.18, freshness: 0.09 },
  },
  {
    mono: "LZ",
    title: "Business Analyst Intern",
    place: "Lazarde & Co. · London",
    why: "Strong skills match",
    tag: "First seen 12 days ago",
    score: 81,
    fx: { profile: 0.33, preference: 0.21, deadline: 0.19, freshness: 0.08 },
  },
];

export const NEWCOMER: Match = {
  mono: "JP",
  title: "Investment Banking Summer Analyst",
  place: "J.P. Morrow · London",
  why: "Strong fit · 7 of 8 skills",
  tag: "New · first seen today",
  score: 91,
  fx: { profile: 0.35, preference: 0.24, deadline: 0.17, freshness: 0.15 },
  isNew: true,
};

export const HERO5 = { x: 1455, y: 600, w: 580 }; // where the new role is examined (centre)

export const T5 = {
  emerge: CUE.hero, // born at the edge (f1200)
  checks: [CUE.check1, CUE.check2] as const,
  listIn: CUE.check1 - 16, // your list, on the left
  lift: CUE.lift, // anticipation
  fly: { from: CUE.lift + 8, to: CUE.land }, // into #1
  shift: CUE.lift + 12, // the others make room
  ring: { from: CUE.land + 2, to: CUE.land + 26 }, // the edge wraps #1
};
