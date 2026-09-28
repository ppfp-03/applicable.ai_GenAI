import React, { useMemo } from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { APP, FONT, SAFE } from "../brand/tokens";
import { Camera, Cam, drift } from "../fx/Camera";
import { Words } from "../fx/Words";
import { E, mix, prog, SPR, springAt } from "../lib/anim";
import { fitLines } from "../lib/measure";
import { FreshCard } from "../product/ui";
import { ACT, CUE, H, W } from "../timeline";
import { COPY } from "../copy";
import { FIELD, FieldRole, FRESH, LANES, NOW4, scaleForAge, STALE, TICKS, xForAge } from "./act4-data";

// ACT 4 - FIND WHAT'S FRESH (0:14-0:20)
// The edge slides to its place and Applicable.ai's view of the opportunity set unfolds out of it:
// every role sits as far from now as it is old. Older roles sink back one per beat; fresh ones are
// born at the edge with a ping. The axis says what the ages are: when Applicable.ai first saw them.

const A = ACT.fresh.from;
const CARD_W = 400;
const CARD_H = (150 * CARD_W) / 340;
export const EDGE_SLIDE = { from: A, to: A + 46 };
export const PUSH4 = { from: CUE.push4, to: ACT.actFirst.from };

export const act4Camera = (f: number): Cam => {
  const d = drift(f, "a4", 2.2);
  const p = prog(f, PUSH4.from, PUSH4.to, E.push);
  return { x: mix(960, 1010, p) + d.dx, y: mix(540, 560, p) + d.dy, s: mix(1, 1.05, p) };
};

/** Where the now edge is in this act (world x, top, bottom). */
export const edge4 = (f: number) => {
  const p = prog(f, EDGE_SLIDE.from, EDGE_SLIDE.to, E.cam);
  return { x: mix(W / 2, NOW4, p), top: mix(-30, FIELD.top - 10, p), bottom: mix(H + 30, FIELD.axisY, p) };
};

const staleState = (r: FieldRole, f: number) => {
  const delay = (1 - r.days / 18) * 14;
  const out = prog(f, A + 6 + delay, A + 50 + delay, E.out);
  const rec = r.recede !== undefined ? prog(f, r.recede, r.recede + 26, E.inOut) : prog(f, CUE.push4 - 30, CUE.push4, E.smooth) * 0.45;
  const s0 = scaleForAge(r.days);
  return {
    x: mix(NOW4, xForAge(r.days), out),
    y: LANES[r.lane] - 26 * rec,
    s: mix(0.5, s0, out) * mix(1, 0.84, rec),
    o: out * mix(1, 0.36, rec),
    blur: 2.4 * rec,
    sat: 1 - rec,
  };
};

const freshState = (r: FieldRole, f: number) => {
  const t = f - (r.emerge ?? 0);
  const p = springAt(t, SPR.land);
  return {
    x: mix(NOW4 - 40, xForAge(r.days), p),
    y: LANES[r.lane],
    s: mix(0.55, 1.04, Math.min(1.2, p)),
    o: Math.min(1, t / 6),
    glow: mix(1, 0.3, prog(f, (r.emerge ?? 0) + 10, (r.emerge ?? 0) + 60, E.smooth)),
    ring: prog(f, r.emerge ?? 0, (r.emerge ?? 0) + 36, E.out),
  };
};

export const FieldCards: React.FC<{ f: number }> = ({ f }) => (
  <>
    {STALE.map((r, i) => {
      const s = staleState(r, f);
      if (s.o <= 0) return null;
      return (
        <div
          key={`s${i}`}
          style={{
            position: "absolute",
            left: s.x - CARD_W / 2,
            top: s.y - CARD_H / 2,
            transform: `scale(${s.s.toFixed(4)})`,
            opacity: s.o,
            filter: `blur(${s.blur.toFixed(2)}px) saturate(${s.sat.toFixed(3)})`,
          }}
        >
          <FreshCard mono={r.mono} title={r.title} place={r.place} age={r.label} kind="stale" w={CARD_W} />
        </div>
      );
    })}
    {FRESH.map((r, i) => {
      if (f < (r.emerge ?? 0)) return null;
      const s = freshState(r, f);
      return (
        <React.Fragment key={`n${i}`}>
          {/* the detection ping: a ring leaves the edge where the role is born */}
          {s.ring < 1 && (
            <div
              style={{
                position: "absolute",
                left: NOW4 - 90 * s.ring - 10,
                top: LANES[r.lane] - 90 * s.ring - 10,
                width: 20 + 180 * s.ring,
                height: 20 + 180 * s.ring,
                borderRadius: "50%",
                border: `3px solid ${APP.orange}`,
                opacity: (1 - s.ring) * 0.8,
              }}
            />
          )}
          <div
            style={{
              position: "absolute",
              left: s.x - CARD_W / 2,
              top: s.y - CARD_H / 2,
              transform: `scale(${s.s.toFixed(4)})`,
              opacity: s.o,
            }}
          >
            <FreshCard mono={r.mono} title={r.title} place={r.place} age={r.label} kind={r.kind} w={CARD_W} glow={s.glow} />
          </div>
        </React.Fragment>
      );
    })}
  </>
);

/** The now edge in the product's own style: an orange hairline with its label. */
export const AppEdge: React.FC<{ x: number; top: number; bottom: number; label: number; w?: number }> = ({ x, top, bottom, label, w = 4 }) => (
  <>
    <div style={{ position: "absolute", left: x - w / 2, top, width: w, height: bottom - top, background: APP.orange, borderRadius: w / 2 }} />
    {label > 0 && (
      <div
        style={{
          position: "absolute",
          left: x - 60,
          width: 120,
          textAlign: "center",
          top: top - 40,
          fontFamily: FONT.app,
          fontSize: 20,
          fontWeight: 700,
          color: APP.orange,
          opacity: label,
        }}
      >
        Now
      </div>
    )}
  </>
);

const Axis: React.FC<{ f: number }> = ({ f }) => {
  const p = prog(f, A + 20, A + 70, E.out);
  const left = mix(NOW4, FIELD.left, p);
  return (
    <>
      <div style={{ position: "absolute", left, top: FIELD.axisY, width: NOW4 - left, height: 2, background: APP.line }} />
      {TICKS.map(([d, label]) => {
        const x = xForAge(d);
        const o = prog(f, A + 24 + (1 - d / 21) * 10, A + 50 + (1 - d / 21) * 10, E.out);
        return (
          <React.Fragment key={d}>
            <div style={{ position: "absolute", left: x - 1, top: FIELD.axisY - 6, width: 2, height: 14, background: APP.line, opacity: o }} />
            <div
              style={{ position: "absolute", left: x - 80, width: 160, textAlign: "center", top: FIELD.axisY + 18, fontFamily: FONT.app, fontSize: 20, fontWeight: 500, color: APP.ink3, opacity: o }}
            >
              {label}
            </div>
          </React.Fragment>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: FIELD.left,
          top: FIELD.axisY + 18,
          fontFamily: FONT.app,
          fontSize: 17,
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: APP.ink2,
          opacity: prog(f, A + 40, A + 70, E.out),
        }}
      >
        First seen by Applicable.ai
      </div>
    </>
  );
};

export const Act4Freshness: React.FC = () => {
  const f = useCurrentFrame() + A;
  const cam = act4Camera(f);
  const e = edge4(f);
  const size = useMemo(
    () => fitLines(["See what matters", "while it still matters."], 1300, { size: 112, weight: 800, track: -0.045 }),
    [],
  );
  const hOut = CUE.headline4Out;

  return (
    <AbsoluteFill style={{ background: APP.bg, overflow: "hidden" }}>
      <Img src={staticFile("fx/app-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      <Camera cam={cam}>
        <Axis f={f} />
        <FieldCards f={f} />
        <AppEdge x={e.x} top={e.top} bottom={e.bottom} label={prog(f, A + 30, A + 56, E.out)} />
      </Camera>
      <div
        style={{
          position: "absolute",
          left: SAFE.x,
          top: 104,
          fontFamily: FONT.app,
          fontWeight: 800,
          fontSize: size,
          letterSpacing: "-0.045em",
          lineHeight: 1.04,
          color: APP.ink,
        }}
      >
        <div>
          <Words text={COPY.seeWhat.text} f={f} start={COPY.seeWhat.start} stagger={COPY.seeWhat.stagger} out={hOut} />
        </div>
        <div>
          <Words
            text={COPY.whileIt.text}
            f={f}
            start={COPY.whileIt.start}
            stagger={COPY.whileIt.stagger}
            out={hOut + 3}
            wordStyle={(i) => (i === 2 ? { color: APP.orange } : {})}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};

