import React from "react";
import { APP, FONT } from "../brand/tokens";

// Applicable.ai UI pieces, rebuilt from the shipping app (Explore tiles, Matches rows, rule chips;
// ui/css/*.css) at film scale. Geometry and wording follow the product; the data is fictional.

export const Mono: React.FC<{ text: string; size: number; tone?: number }> = ({ text, size, tone = 0 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.24,
      background: tone === 0 ? APP.mono : tone === 1 ? "#3A3A3E" : "#636368",
      color: "#fff",
      display: "grid",
      placeItems: "center",
      fontFamily: FONT.app,
      fontWeight: 700,
      fontSize: size * 0.34,
      letterSpacing: "0.01em",
      flexShrink: 0,
    }}
  >
    {text}
  </div>
);

export const Check: React.FC<{ size: number; color?: string; bg?: string }> = ({ size, color = APP.green, bg = APP.greenBg }) => (
  <div style={{ width: size, height: size, borderRadius: size / 2, background: bg, display: "grid", placeItems: "center", flexShrink: 0 }}>
    <svg width={size * 0.58} height={size * 0.58} viewBox="0 0 16 16">
      <path d="M3 8.5 6.3 12 13 4.5" stroke={color} strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  </div>
);

/** The product's RULE source tag. */
export const RuleTag: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      height: size * 1.5,
      padding: `0 ${size * 0.45}px`,
      border: `1px solid ${APP.ink3}`,
      borderRadius: size * 0.3,
      fontSize: size * 0.82,
      fontWeight: 700,
      letterSpacing: "0.08em",
      color: APP.ink2,
    }}
  >
    RULE
  </span>
);

export type Fresh = "new" | "fresh" | "stale";

/** How long ago the system first saw a role. Fresh is warm; stale is grey and quiet. */
export const AgeChip: React.FC<{ label: string; kind: Fresh; size?: number }> = ({ label, kind, size = 16 }) => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: size * 0.45,
      height: size * 1.75,
      padding: `0 ${size * 0.7}px`,
      borderRadius: size,
      fontFamily: FONT.app,
      fontSize: size,
      fontWeight: kind === "stale" ? 600 : 700,
      background: kind === "new" ? APP.orange : kind === "fresh" ? APP.orangeBg : APP.line2,
      color: kind === "new" ? "#fff" : kind === "fresh" ? APP.orangeInk : APP.ink3,
      whiteSpace: "nowrap",
    }}
  >
    {kind !== "stale" && (
      <span style={{ width: size * 0.5, height: size * 0.5, borderRadius: size, background: kind === "new" ? "#fff" : APP.orange }} />
    )}
    {label}
  </span>
);

/** Explore tile, as in the app's Explore grid (mono, priority, role, place, bar, status). */
export const ExploreTile: React.FC<{
  mono: string;
  title: string;
  place: string;
  score: number;
  status: "Eligible" | "To verify";
  bar: number;
  w?: number;
}> = ({ mono, title, place, score, status, bar, w = 220 }) => {
  const k = w / 220;
  return (
    <div
      style={{
        width: w,
        height: 150 * k,
        borderRadius: 18 * k,
        background: APP.surface,
        boxShadow: "0 1px 2px rgba(64,40,28,0.05), 0 8px 24px rgba(64,40,28,0.07)",
        padding: 16 * k,
        boxSizing: "border-box",
        fontFamily: FONT.app,
        color: APP.ink,
        position: "relative",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Mono text={mono} size={34 * k} tone={status === "Eligible" ? 0 : 2} />
        <div style={{ textAlign: "right", lineHeight: 1 }}>
          <div style={{ fontSize: 26 * k, fontWeight: 800, letterSpacing: "-0.03em" }}>{score}</div>
          <div style={{ fontSize: 11 * k, color: APP.ink3, marginTop: 3 * k }}>{status === "Eligible" ? "Priority" : "To verify"}</div>
        </div>
      </div>
      <div style={{ fontSize: 15 * k, fontWeight: 700, marginTop: 12 * k, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{title}</div>
      <div style={{ fontSize: 12.5 * k, color: APP.ink2, marginTop: 2 * k, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{place}</div>
      <div style={{ position: "absolute", left: 16 * k, right: 16 * k, bottom: 16 * k, height: 4 * k, borderRadius: 2 * k, background: APP.line2 }}>
        <div style={{ width: `${bar * 100}%`, height: "100%", borderRadius: 2 * k, background: APP.orange }} />
      </div>
    </div>
  );
};

/** One role in the freshness field: who, where, and how long ago Applicable.ai first saw it. */
export const FreshCard: React.FC<{
  mono: string;
  title: string;
  place: string;
  age: string;
  kind: Fresh;
  w?: number;
  glow?: number;
}> = ({ mono, title, place, age, kind, w = 340, glow = 0 }) => {
  const k = w / 340;
  return (
    <div
      style={{
        width: w,
        height: 150 * k,
        borderRadius: 20 * k,
        background: APP.surface,
        boxShadow:
          glow > 0
            ? `0 0 0 ${2.5 * k * glow}px rgba(242,106,61,${0.9 * glow}), 0 12px 36px rgba(242,106,61,${0.22 * glow}), 0 8px 24px rgba(64,40,28,0.07)`
            : "0 1px 2px rgba(64,40,28,0.05), 0 8px 24px rgba(64,40,28,0.07)",
        padding: `${18 * k}px ${20 * k}px`,
        boxSizing: "border-box",
        fontFamily: FONT.app,
        color: APP.ink,
      }}
    >
      <div style={{ display: "flex", gap: 14 * k, alignItems: "center" }}>
        <Mono text={mono} size={46 * k} tone={kind === "stale" ? 2 : 0} />
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 20 * k, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", width: 236 * k, letterSpacing: "-0.01em" }}>
            {title}
          </div>
          <div style={{ fontSize: 15.5 * k, color: APP.ink2, marginTop: 3 * k, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", width: 236 * k }}>
            {place}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 18 * k }}>
        <AgeChip label={age} kind={kind} size={15.5 * k} />
      </div>
    </div>
  );
};

export type Factors = { profile: number; preference: number; deadline: number; freshness: number };

/** The four ranking factor families as the app draws them: one stacked bar, freshness last. */
export const FactorBar: React.FC<{ fx: Factors; w: number; h?: number; freshGlow?: number }> = ({ fx, w, h = 10, freshGlow = 0 }) => {
  const segs = [
    { v: fx.profile, c: APP.orange },
    { v: fx.preference, c: APP.orange2 },
    { v: fx.deadline, c: APP.orange3 },
    { v: fx.freshness, c: freshGlow > 0 ? mixHex(APP.orange4, "#F7A07B", freshGlow) : APP.orange4 },
  ];
  return (
    <div style={{ width: w, height: h, borderRadius: h / 2, background: APP.line2, display: "flex", gap: 2, overflow: "hidden" }}>
      {segs.map((s, i) => (
        <div key={i} style={{ width: `${s.v * 100}%`, height: "100%", background: s.c }} />
      ))}
    </div>
  );
};

export const mixHex = (a: string, b: string, t: number) => {
  const pa = [1, 3, 5].map((k) => parseInt(a.slice(k, k + 2), 16));
  const pb = [1, 3, 5].map((k) => parseInt(b.slice(k, k + 2), 16));
  return `rgb(${pa.map((v, k) => Math.round(v + (pb[k] - v) * t)).join(",")})`;
};

export type Match = {
  mono: string;
  title: string;
  place: string;
  why: string;
  tag?: string;
  score: number;
  fx: Factors;
  isNew?: boolean;
};

export const ROW = { w: 1020, h: 112 };

/** A row of "Your top matches", as in the app's Matches list. */
export const MatchRow: React.FC<{ m: Match; rank: number; active?: number; freshGlow?: number; dim?: number }> = ({
  m,
  rank,
  active = 0,
  freshGlow = 0,
  dim = 0,
}) => (
  <div
    style={{
      width: ROW.w,
      height: ROW.h,
      borderRadius: 18,
      background: APP.surface,
      boxShadow: `0 1px 2px rgba(64,40,28,0.05), 0 8px 24px rgba(64,40,28,${0.06 + 0.08 * active})`,
      display: "flex",
      alignItems: "center",
      padding: "0 28px",
      gap: 22,
      boxSizing: "border-box",
      fontFamily: FONT.app,
      color: APP.ink,
      opacity: 1 - dim * 0.55,
      filter: dim > 0.01 ? `saturate(${1 - dim})` : undefined,
    }}
  >
    <div style={{ width: 30, fontSize: 30, fontWeight: 700, textAlign: "center", fontVariantNumeric: "tabular-nums" }}>{rank}</div>
    <Mono text={m.mono} size={50} />
    <div style={{ width: 290, minWidth: 0 }}>
      <div style={{ fontSize: 22, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", letterSpacing: "-0.01em" }}>{m.title}</div>
      <div style={{ fontSize: 17, color: APP.ink2, marginTop: 3 }}>{m.place}</div>
    </div>
    <div style={{ width: 214 }}>
      <div style={{ fontSize: 17.5, fontWeight: 600, whiteSpace: "nowrap" }}>{m.why}</div>
      {m.tag && (
        <div style={{ marginTop: 6 }}>
          <AgeChip label={m.tag} kind={m.isNew ? "new" : "stale"} size={13.5} />
        </div>
      )}
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 17, fontWeight: 600, color: APP.green, width: 96 }}>
      <span style={{ width: 9, height: 9, borderRadius: 5, background: APP.green }} />
      Eligible
    </div>
    <FactorBar fx={m.fx} w={110} freshGlow={freshGlow} />
    <div style={{ marginLeft: "auto", fontSize: 40, fontWeight: 800, letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums" }}>{m.score}</div>
  </div>
);
