import React, { useMemo } from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { evolvePath } from "@remotion/paths";
import { APP, FONT, SAFE } from "../brand/tokens";
import { Camera, Cam, drift } from "../fx/Camera";
import { Words } from "../fx/Words";
import { E, hitPulse, mix, prog, SPR, springAt } from "../lib/anim";
import { fitLines } from "../lib/measure";
import { AgeChip, Check, MatchRow, Mono, ROW, RuleTag } from "../product/ui";
import { ACT, CUE, H, W } from "../timeline";
import { COPY } from "../copy";
import { act4Camera, AppEdge, edge4, FieldCards } from "./Act4Freshness";
import { NOW4 } from "./act4-data";
import { EXISTING, HERO5, LIST, LIST_CAM, NEWCOMER, slotY, T5 } from "./act5-data";

// ACT 5 - ACT FIRST (0:20-0:25)
// A strong new role is born at the edge. Applicable.ai looks at it: fit, then the rules. It lifts
// out of the field and lands at #1 of your top matches; the others make room. The now edge wraps
// it: this is where you move first.

const A = ACT.actFirst.from;

const HERO_H = 362; // the hero card's fixed height at HERO5.w

/** The new role, examined: who, where, when first seen, and the two checks. */
const HeroCard: React.FC<{ f: number; w: number }> = ({ f, w }) => {
  const k = w / HERO5.w;
  const c1 = prog(f, T5.checks[0], T5.checks[0] + 16, E.out);
  const c2 = prog(f, T5.checks[1], T5.checks[1] + 16, E.out);
  const pop1 = hitPulse(f - T5.checks[0], 2, 5);
  const pop2 = hitPulse(f - T5.checks[1], 2, 5);
  return (
    <div
      style={{
        width: HERO5.w,
        height: HERO_H,
        transformOrigin: "0 0",
        transform: `scale(${k})`,
        borderRadius: 26,
        background: APP.surface,
        padding: "30px 34px 28px",
        boxSizing: "border-box",
        fontFamily: FONT.app,
        color: APP.ink,
        boxShadow: "0 0 0 3px rgba(242,106,61,0.9), 0 24px 60px rgba(242,106,61,0.20), 0 10px 30px rgba(64,40,28,0.10)",
      }}
    >
      <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
        <Mono text={NEWCOMER.mono} size={62} />
        <div>
          <div style={{ fontSize: 29, fontWeight: 800, letterSpacing: "-0.02em", lineHeight: 1.12 }}>
            Investment Banking
            <br />
            Summer Analyst
          </div>
          <div style={{ fontSize: 20, color: APP.ink2, marginTop: 4 }}>J.P. Morrow · London · Summer 2027</div>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 22 }}>
        <AgeChip label="New" kind="new" size={18} />
        <span style={{ fontSize: 19, fontWeight: 600, color: APP.orangeInk }}>First seen today, 09:12</span>
      </div>
      <div style={{ height: 1, background: APP.line, margin: "24px 0 18px" }} />
      <div style={{ display: "flex", alignItems: "center", gap: 14, height: 40, opacity: c1, transform: `translateY(${(1 - c1) * 10}px)` }}>
        <div style={{ transform: `scale(${1 + pop1 * 0.25})` }}>
          <Check size={30} />
        </div>
        <span style={{ fontSize: 21, fontWeight: 600 }}>Strong fit</span>
        <span style={{ fontSize: 20, color: APP.ink2 }}>7 of 8 key skills</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, height: 40, marginTop: 8, opacity: c2, transform: `translateY(${(1 - c2) * 10}px)` }}>
        <div style={{ transform: `scale(${1 + pop2 * 0.25})` }}>
          <Check size={30} />
        </div>
        <RuleTag size={15} />
        <span style={{ fontSize: 21, fontWeight: 600 }}>Eligible under checked rules</span>
      </div>
    </div>
  );
};


export const act5Camera = (f: number): Cam => {
  const d = drift(f, "a5", 2.2);
  const start = act4Camera(A);
  const back = prog(f, A, A + 70, E.smooth);
  const kick = hitPulse(f - CUE.land, 1.5, 8) * 0.018;
  const frame = prog(f, CUE.land - 6, CUE.land + 44, E.cam);
  const creep = prog(f, CUE.land + 44, ACT.edge.from + 20, E.smooth) * 0.02;
  return {
    x: mix(mix(start.x, 960, back), LIST_CAM.x, frame) + d.dx,
    y: mix(mix(start.y, 540, back), LIST_CAM.y, frame) + d.dy,
    s: mix(mix(start.s, 1, back), LIST_CAM.s, frame) + kick + creep,
  };
};

/** Row i's y for the three existing matches: they make room for the newcomer. */
export const existingY = (i: number, f: number) => {
  const p = springAt(f - (T5.shift + i * 3), SPR.land);
  return mix(slotY(i), slotY(i + 1), p);
};

/** The newcomer's rect: examined at centre, then lifted into #1 (card -> row). */
export const heroRect = (f: number) => {
  const born = springAt(f - T5.emerge, SPR.land);
  const lift = hitPulse(f - T5.lift, 6, 10) * 0.035;
  const fly = prog(f, T5.fly.from, T5.fly.to, E.inOut);
  const settle = f >= T5.fly.to ? springAt(f - T5.fly.to, SPR.snap) : 0;
  const cardW = mix(HERO5.w * 0.5, HERO5.w, born) * (1 + lift);
  const cardH = HERO_H * (cardW / HERO5.w);
  const cx = mix(NOW4, HERO5.x, born);
  const cy = HERO5.y;
  const rowCx = LIST.x + ROW.w / 2;
  const rowCy = slotY(0) + ROW.h / 2 + (1 - settle) * 10 * (f >= T5.fly.to ? 1 : 0);
  const w = mix(cardW, ROW.w, fly);
  const h = mix(cardH, ROW.h, fly);
  return { x: mix(cx, rowCx, fly) - w / 2, y: mix(cy, rowCy, fly) - h / 2, w, h, fly };
};

/** The now edge wrapping #1: its outline, drawn from the left edge as the row lands. */
export const RowRing: React.FC<{ p: number; x: number; y: number; o?: number }> = ({ p, x, y, o = 1 }) => {
  if (p <= 0) return null;
  const r = 18;
  const w = ROW.w + 8;
  const h = ROW.h + 8;
  // start mid-left and run both ways round so it closes on the right
  const d = `M 0 ${h / 2} L 0 ${r} Q 0 0 ${r} 0 L ${w - r} 0 Q ${w} 0 ${w} ${r} L ${w} ${h - r} Q ${w} ${h} ${w - r} ${h} L ${r} ${h} Q 0 ${h} 0 ${h - r} Z`;
  const ev = evolvePath(p, d);
  return (
    <svg width={w + 8} height={h + 8} style={{ position: "absolute", left: x - 8, top: y - 8, overflow: "visible", opacity: o }}>
      <path d={d} transform="translate(4 4)" fill="none" stroke={APP.orange} strokeWidth={4} strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
    </svg>
  );
};

export const ListHeader: React.FC<{ o: number }> = ({ o }) => (
  <div style={{ position: "absolute", left: LIST.x + 6, top: LIST.headerY, width: ROW.w - 12, display: "flex", alignItems: "baseline", fontFamily: FONT.app, opacity: o }}>
    <span style={{ fontSize: 24, fontWeight: 700, color: APP.ink }}>Your top matches</span>
    <span style={{ fontSize: 17, color: APP.ink3, marginLeft: 14 }}>Ordered by priority score</span>
    <span style={{ marginLeft: "auto", display: "flex", gap: 18, fontSize: 16, color: APP.ink2 }}>
      {[
        ["Profile", APP.orange],
        ["Preference", APP.orange2],
        ["Deadline urgency", APP.orange3],
        ["Freshness", APP.orange4],
      ].map(([t, c]) => (
        <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
          <span style={{ width: 11, height: 11, borderRadius: 3, background: c }} />
          {t}
        </span>
      ))}
    </span>
  </div>
);

export const Act5ActFirst: React.FC = () => {
  const f = useCurrentFrame() + A;
  const cam = act5Camera(f);
  const e = edge4(f);
  const fieldAway = prog(f, A, A + 44, E.smooth);
  const listIn = prog(f, T5.listIn, T5.listIn + 30, E.out);
  const hr = heroRect(f);
  const toRow = prog(f, T5.fly.from + 4, T5.fly.to - 2, E.smooth);

  // the edge leaves its post and becomes #1's outline
  const go = prog(f, T5.fly.from, T5.fly.to, E.inOut);
  const edgeX = mix(e.x, LIST.x - 4, go);
  const edgeTop = mix(e.top, slotY(0) - 4, go);
  const edgeBot = mix(e.bottom, slotY(0) + ROW.h + 4, go);
  const ringP = prog(f, T5.ring.from, T5.ring.to, E.out);

  const size = useMemo(() => fitLines(["Know where to move first."], W - 2 * SAFE.x, { size: 116, weight: 800, track: -0.045 }), []);

  return (
    <AbsoluteFill style={{ background: APP.bg, overflow: "hidden" }}>
      <Img src={staticFile("fx/app-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      <Camera cam={cam}>
        {/* the field steps back: this one role is what matters now */}
        <div style={{ position: "absolute", inset: 0, opacity: mix(1, 0.0, fieldAway), filter: `blur(${(fieldAway * 5).toFixed(2)}px)` }}>
          <FieldCards f={Math.min(f, A)} />
        </div>

        {/* your top matches, already there */}
        <ListHeader o={listIn} />
        {EXISTING.map((m, i) => {
          const y = existingY(i, f);
          const rank = springAt(f - (T5.shift + i * 3), SPR.land) > 0.5 ? i + 2 : i + 1;
          return (
            <div key={m.mono} style={{ position: "absolute", left: LIST.x - (1 - listIn) * 80, top: y, opacity: listIn }}>
              <MatchRow m={m} rank={rank} />
            </div>
          );
        })}

        {/* the edge, then #1's outline */}
        {ringP < 1 && f < T5.fly.to + 4 && <AppEdge x={edgeX} top={edgeTop} bottom={edgeBot} label={1 - go * 3} />}
        <RowRing p={ringP} x={LIST.x - 4} y={(f >= T5.fly.to ? hr.y : slotY(0)) - 4} />

        {/* the newcomer: card -> row */}
        {f >= T5.emerge && (
          <div
            style={{
              position: "absolute",
              left: hr.x,
              top: hr.y,
              width: hr.w,
              height: hr.h,
              borderRadius: mix(26, 18, hr.fly),
              overflow: "hidden",
              boxShadow: `0 ${mix(24, 10, hr.fly)}px ${mix(60, 30, hr.fly)}px rgba(64,40,28,${mix(0.16, 0.1, hr.fly)})`,
              background: APP.surface,
            }}
          >
            <div style={{ position: "absolute", left: 0, top: 0, opacity: 1 - toRow }}>
              <HeroCard f={f} w={hr.w} />
            </div>
            <div style={{ position: "absolute", left: 0, top: 0, opacity: toRow, transformOrigin: "0 0", transform: `scale(${hr.w / ROW.w}, ${hr.h / ROW.h})` }}>
              <MatchRow m={NEWCOMER} rank={1} freshGlow={prog(f, CUE.land, CUE.land + 20, E.out)} />
            </div>
          </div>
        )}
      </Camera>

      {/* "Know where to move first." */}
      <div
        style={{
          position: "absolute",
          left: 0,
          width: W,
          top: 92,
          textAlign: "center",
          fontFamily: FONT.app,
          fontWeight: 800,
          fontSize: size,
          letterSpacing: "-0.045em",
          lineHeight: 1.05,
          color: APP.ink,
        }}
      >
        <Words
          text={COPY.knowWhere.text}
          f={f}
          start={COPY.knowWhere.start}
          stagger={COPY.knowWhere.stagger}
          dur={20}
          wordStyle={(i) => (i === 4 ? { color: APP.orange } : {})}
        />
      </div>
    </AbsoluteFill>
  );
};
