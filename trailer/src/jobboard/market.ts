import { clamp, rand } from "../lib/anim";
import { ACT, CUE } from "../timeline";

// The market as a river of time. Space is age: every posting enters at the now edge and drifts
// away from it as it ages, collecting applicants and running out of deadline. Deterministic, so
// the picture and the cue exporter agree about every posting at every frame.

export const NOW_X = 1480; // world x of the now edge
export const PX_PER_DAY = 200; // one day of age = 200 px of distance from now
export const CARD = { w: 260, h: 96 };

// The world clock (days since the pull-back). It starts slowly and keeps accelerating through the
// act: time is running away. After the ignition it coasts to a stop (the market stops pushing).
const D_TOTAL = 7.5;
const T0 = CUE.pullBack;
const T1 = ACT.reveal.from;
const V_END = (D_TOTAL * (0.35 + 3 * 0.65)) / (T1 - T0); // days per frame at the ignition
const COAST = 22; // frames

export const dayAt = (f: number) => {
  if (f <= T0) return 0;
  if (f <= T1) {
    const u = (f - T0) / (T1 - T0);
    return D_TOTAL * (0.35 * u + 0.65 * u * u * u);
  }
  return D_TOTAL + V_END * COAST * (1 - Math.exp(-(f - T1) / COAST));
};

const ROLES = [
  "Summer Analyst · M&A",
  "Spring Insight Week",
  "Graduate Programme · Strategy",
  "Off-cycle Intern · DCM",
  "Audit Associate",
  "Markets Summer Intern",
  "Consulting Summer Intern",
  "Product Analyst Intern",
  "Equity Research Intern",
  "Risk Analyst · Graduate",
  "Private Equity Intern",
  "Transaction Services Intern",
  "Corporate Finance Intern",
  "Asset Management Intern",
  "Treasury Graduate",
  "Business Analyst Intern",
  "Strategy & Deals Associate",
  "Leveraged Finance Intern",
];
const COMPANIES: [string, string][] = [
  ["Lazarde & Co.", "LZ"],
  ["Bolton Consulting Group", "BC"],
  ["Nestella", "NE"],
  ["Roshe", "RO"],
  ["Morgan Stanfield", "MS"],
  ["UniCreda", "UC"],
  ["Deutsch Bank", "DB"],
  ["Mediobanco", "MB"],
  ["Replai", "RP"],
  ["AlphaBridge Advisory", "AA"],
  ["Lendwell Analytics", "LA"],
  ["Cairnholm Advisory", "CA"],
  ["Insurient Consulting", "IC"],
  ["Rainford Merchant Bank", "RM"],
];
const CITIES = ["London", "Milan", "Zurich", "Paris", "Frankfurt", "Amsterdam", "Madrid", "Dublin"];

export type Posting = {
  id: string;
  lane: number;
  layer: 0 | 1; // 0 = front, 1 = deep
  born: number; // world day
  title: string;
  company: string;
  mono: string;
  city: string;
  pop: number; // how fast it collects applicants
  closeIn: number; // days from birth to its deadline
  hero?: boolean;
};

export const HERO_ID = "hero";
export const HERO_LANE = 3;
export const HERO_BORN = -3;

export const LAYERS = [
  { lanes: 7, top: 140, pitch: 118, scale: 1, from: -9, to: 12 },
  { lanes: 15, top: -380, pitch: 118, scale: 0.56, from: -16, to: 14 },
] as const;

export const laneTop = (layer: 0 | 1, lane: number) => LAYERS[layer].top + lane * LAYERS[layer].pitch;

const build = (): Posting[] => {
  const out: Posting[] = [];
  LAYERS.forEach((L, layer) => {
    for (let lane = 0; lane < L.lanes; lane++) {
      const seed = `${layer}-${lane}`;
      let d = L.from + rand(seed + "o") * 1.6;
      let k = 0;
      while (d < L.to) {
        const isHeroLane = layer === 0 && lane === HERO_LANE;
        // keep the hero's slot clear: neighbours sit at least 1.5 days away from it
        if (isHeroLane && Math.abs(d - HERO_BORN) < 1.5) d = HERO_BORN + 1.5;
        const r = (s: string) => rand(`${seed}-${k}-${s}`);
        const [company, mono] = COMPANIES[Math.floor(r("c") * COMPANIES.length)];
        out.push({
          id: `${seed}-${k}`,
          lane,
          layer: layer as 0 | 1,
          born: d,
          title: ROLES[Math.floor(r("t") * ROLES.length)],
          company,
          mono,
          city: CITIES[Math.floor(r("y") * CITIES.length)],
          pop: 0.55 + r("p") * 1.1,
          closeIn: 3.5 + r("d") * 14,
        });
        d += 1.45 + r("g") * 0.95;
        k++;
      }
    }
  });
  out.push({
    id: HERO_ID,
    lane: HERO_LANE,
    layer: 0,
    born: HERO_BORN,
    title: "Investment Banking Summer Analyst",
    company: "Lazarde & Co.",
    mono: "LZ",
    city: "London",
    pop: 1.4,
    closeIn: 21,
    hero: true,
  });
  return out;
};

export const MARKET = build();

export const ageOf = (p: Posting, day: number) => day - p.born;
export const applicantsAt = (p: Posting, age: number) =>
  p.hero ? 100 : Math.max(0, Math.round(p.pop * 21 * Math.pow(Math.max(0, age), 0.9)));

/**
 * Left edge x (world) of a posting at a given age. A new posting slides out from behind the now
 * edge (the river is clipped at NOW_X: nothing exists in the future), then keeps drifting away.
 */
export const leftX = (age: number) => NOW_X - age * PX_PER_DAY;

export const ageLabel = (age: number) => {
  if (age < 1 / 24) return "Just now";
  if (age < 1) return `${Math.max(1, Math.floor(age * 24))}h ago`;
  return `${Math.floor(age)}d ago`;
};

export const fadeWithAge = (age: number) => clamp(1 - (age - 1.5) / 9, 0.32, 1);
