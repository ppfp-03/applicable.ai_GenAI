import { CUE } from "../timeline";

// ACT 4 data: the freshness field. Space is age again, now in Applicable.ai's own terms: the axis
// is when Applicable.ai FIRST SAW a role (a labelled discovery time, as the product's freshness
// factor uses it), not a publication date the source never gave us. Illustrative roles.

export const NOW4 = 1560; // x of the now edge in this act
export const FIELD = { top: 396, axisY: 948, left: 150 };
export const LANES = [478, 658, 838]; // card centre y

/** Card centre x for an age in days: the last day gets the most room, three weeks the least. */
export const xForAge = (days: number) => NOW4 - 240 - 1150 * Math.sqrt(days / 21);
export const scaleForAge = (days: number) => 1 - 0.2 * Math.sqrt(Math.min(days, 21) / 21);

export type FieldRole = {
  mono: string;
  title: string;
  place: string;
  days: number;
  lane: number;
  label: string;
  kind: "stale" | "fresh" | "new";
  recede?: number; // frame it sinks back
  emerge?: number; // frame it is born at the edge
};

export const STALE: FieldRole[] = [
  { mono: "NE", title: "Graduate Programme · Strategy", place: "Nestella · Zurich", days: 18, lane: 0, label: "18 days ago", kind: "stale", recede: CUE.recede[0] },
  { mono: "MS", title: "Spring Insight Week", place: "Morgan Stanfield · London", days: 15, lane: 2, label: "15 days ago", kind: "stale", recede: CUE.recede[1] },
  { mono: "UC", title: "Off-cycle Intern · DCM", place: "UniCreda · Milan", days: 12, lane: 1, label: "12 days ago", kind: "stale", recede: CUE.recede[2] },
  { mono: "MB", title: "Equity Research Intern", place: "Mediobanco · Milan", days: 8, lane: 0, label: "8 days ago", kind: "stale", recede: CUE.recede[3] },
  { mono: "RO", title: "Finance Graduate", place: "Roshe · Basel", days: 6, lane: 2, label: "6 days ago", kind: "stale" },
  { mono: "DB", title: "Treasury Graduate", place: "Deutsch Bank · Frankfurt", days: 4, lane: 1, label: "4 days ago", kind: "stale" },
];

export const FRESH: FieldRole[] = [
  { mono: "LZ", title: "Business Analyst Intern", place: "Lazarde & Co. · London", days: 0.08, lane: 1, label: "2h ago", kind: "fresh", emerge: CUE.emerge[0] },
  { mono: "BC", title: "Strategy Intern", place: "Bolton Consulting Group · London", days: 0.3, lane: 0, label: "Today", kind: "fresh", emerge: CUE.emerge[1] },
  { mono: "RP", title: "Product Analyst Intern", place: "Replai · London", days: 0.02, lane: 2, label: "New", kind: "new", emerge: CUE.emerge[2] },
];

// the axis ticks (days) and their words
export const TICKS: [number, string][] = [
  [14, "2 weeks"],
  [7, "1 week"],
  [3, "3 days"],
  [1, "1 day"],
];
