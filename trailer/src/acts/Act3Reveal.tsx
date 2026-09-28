import React from "react";
import { AbsoluteFill, Easing, Img, staticFile, useCurrentFrame } from "remotion";
import { APP, VOID } from "../brand/tokens";
import { lockupWidth, MarkA, TILE_RADIUS, Wordmark } from "../brand/Mark";
import { Camera } from "../fx/Camera";
import { E, hitPulse, mix, prog, SPR, springAt } from "../lib/anim";
import { River } from "../jobboard/River";
import { NOW_X } from "../jobboard/market";
import { ExploreTile, mixHex } from "../product/ui";
import { ACT, CUE, H, W } from "../timeline";
import { act2Camera } from "./Act2Problem";

// ACT 3 - APPLICABLE.AI (0:10-0:14)
// The now edge ignites. A wave of order runs out from it: the dark market turns into the product's
// light, ranked world. Then the edge itself folds into the Applicable.ai tile, the "A" rises in it
// and the wordmark slides out. At the end the tile unfolds back into the edge: the brand is the
// thing that keeps watching now.

const A = ACT.reveal.from;
export const TILE = 200;
export const LOCK_LEFT = W / 2 - lockupWidth(TILE) / 2;
// the wave leaves the edge fast but visibly, and slows as it reaches the frame's sides
export const WAVE_EASE = Easing.bezier(0.25, 0.1, 0.25, 1);

export const R3 = {
  wave: { from: A, to: CUE.waveEnd }, // f600-652
  collapse: { from: A + 28, to: A + 64 }, // the edge shortens into a square
  widen: A + 50, // and widens (spring); its landing frame is exported as act3.tileLand
  lockShift: { from: CUE.wordmark - 4, to: CUE.wordmark + 32 },
  tuck: { from: CUE.unfold, to: CUE.unfold + 20 },
  back: { from: CUE.unfold, to: CUE.unfold + 24 },
  unfoldW: { from: CUE.unfold + 14, to: ACT.fresh.from },
  unfoldH: { from: CUE.unfold + 12, to: ACT.fresh.from },
};

const GRID = [
  ["RP", "Product Analyst Intern", "Replai · London", 87, "Eligible"],
  ["BC", "Strategy Intern", "Bolton Consulting Group · London", 83, "Eligible"],
  ["LZ", "Business Analyst Intern", "Lazarde & Co. · London", 81, "Eligible"],
  ["MS", "Product Intern", "Morgan Stanfield · London", 77, "Eligible"],
  ["DB", "Product Analyst Intern", "Deutsch Bank · Shanghai", 65, "To verify"],
  ["AA", "Strategy & Deals Associate", "AlphaBridge Advisory · London", 62, "Eligible"],
  ["NE", "Strategy Intern", "Nestella · Singapore", 61, "To verify"],
  ["JP", "Strategy Analyst Intern", "J.P. Morrow · Singapore", 59, "To verify"],
  ["LA", "Growth & Analytics Intern", "Lendwell Analytics · London", 52, "Eligible"],
  ["RO", "Product Intern", "Roshe · Shanghai", 51, "To verify"],
  ["FA", "IBD Intern · January", "Fintech Arc Partners · London", 50, "Eligible"],
  ["NP", "Summer Internship · Trading", "Northstar Pension Markets", 49, "Eligible"],
  ["CA", "Consultant · Intern Hires", "Cairnholm Advisory · London", 49, "Eligible"],
  ["IC", "Insurance Consulting Intern", "Insurient Consulting · London", 49, "Eligible"],
  ["RM", "Summer Analyst Program", "Rainford Merchant Bank · London", 49, "Eligible"],
  ["UC", "Off-cycle Intern · DCM", "UniCreda · Milan", 47, "Eligible"],
  ["MB", "Equity Research Intern", "Mediobanco · Milan", 46, "To verify"],
  ["NE", "Graduate Programme", "Nestella · Zurich", 44, "To verify"],
] as const;
const COLS = 6;
const TW = 236;
const TH = (150 * TW) / 220;
const GAP = 30;
const gridLeft = (W - (COLS * TW + (COLS - 1) * GAP)) / 2;
const gridTop = (H - (3 * TH + 2 * GAP)) / 2;

/** Screen x of the now edge under the (still rushing) camera. */
export const edgeScreenX = (f: number) => {
  const c = act2Camera(f);
  return W / 2 + (NOW_X - c.x) * c.s;
};

/** Geometry of the edge-to-tile shape at frame f (screen space, centre + size). */
export const tileShape = (f: number) => {
  const h1 = prog(f, R3.collapse.from, R3.collapse.to, E.inOut);
  const w1 = springAt(f - R3.widen, SPR.pop);
  const shift = prog(f, R3.lockShift.from, R3.lockShift.to, E.inOut);
  const back = prog(f, R3.back.from, R3.back.to, E.inOut);
  const uw = prog(f, R3.unfoldW.from, R3.unfoldW.to, E.inOut);
  const uh = prog(f, R3.unfoldH.from, R3.unfoldH.to, E.inOut);
  const w = mix(mix(4, TILE, w1), 4, uw);
  const h = mix(mix(H + 60, TILE, h1), H + 60, uh);
  const centre = mix(edgeScreenX(f), W / 2, prog(f, A, R3.collapse.to, E.inOut));
  const cx = mix(mix(centre, LOCK_LEFT + TILE / 2, shift), W / 2, back);
  return { cx, cy: H / 2, w, h, tileness: Math.min(w1, 1) * (1 - uw) };
};

export const Act3Reveal: React.FC = () => {
  const f = useCurrentFrame() + A;

  // the dark market keeps coasting under the wave, the camera still carrying the rush's momentum
  const cam = act2Camera(f);

  // the wave of order: light spreads out from the edge in both directions
  const wave = prog(f, R3.wave.from, R3.wave.to, WAVE_EASE);
  const half = wave * 1960;
  const wx = edgeScreenX(f);
  const ignite = hitPulse(f - A, 2, 9);

  const shape = tileShape(f);
  const color = mixHex(APP.orange, APP.tile, shape.tileness);
  const radius = Math.min(shape.w, shape.h) * TILE_RADIUS;

  const aP = Math.min(1, springAt(f - CUE.aIn, SPR.snap)) * (1 - prog(f, CUE.unfold + 4, CUE.unfold + 12, E.in));
  const reveal = prog(f, CUE.wordmark, CUE.wordmark + 30, E.out) * (1 - prog(f, R3.tuck.from, R3.tuck.to, E.in));
  const hold = mix(1, 1.035, prog(f, CUE.wordmark, CUE.unfold, E.smooth)) * mix(1, 1 / 1.035, prog(f, CUE.unfold, CUE.unfold + 24, E.inOut));

  return (
    <AbsoluteFill style={{ background: VOID.bg, overflow: "hidden" }}>
      {/* the market, still dark outside the wave */}
      {wave < 1 && (
        <AbsoluteFill>
          <Img src={staticFile("fx/void-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
          <Camera cam={cam}>
            <River f={f} />
          </Camera>
        </AbsoluteFill>
      )}

      {/* the product's world, inside the wave */}
      <AbsoluteFill style={{ clipPath: `inset(0 ${Math.max(0, W - wx - half).toFixed(2)}px 0 ${Math.max(0, wx - half).toFixed(2)}px)` }}>
        <Img src={staticFile("fx/app-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
        {GRID.map((g, i) => {
          const col = i % COLS;
          const row = Math.floor(i / COLS);
          const x = gridLeft + col * (TW + GAP);
          const y = gridTop + row * (TH + GAP);
          const dx = x + TW / 2 - W / 2;
          const dy = y + TH / 2 - H / 2;
          const dist = Math.hypot(dx, dy) / 900;
          const inP = prog(f, A + 4 + dist * 16, A + 30 + dist * 16, E.out);
          const absorb = prog(f, A + 30 + (1 - dist) * 14, A + 58 + (1 - dist) * 14, E.in);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x,
                top: y,
                transform: `translate(${(-dx * 0.42 * absorb).toFixed(2)}px, ${(-dy * 0.42 * absorb).toFixed(2)}px) scale(${(mix(1.06, 1, inP) * mix(1, 0.72, absorb)).toFixed(4)})`,
                opacity: inP * (1 - absorb),
              }}
            >
              <ExploreTile mono={g[0]} title={g[1]} place={g[2]} score={g[3]} status={g[4]} bar={g[3] / 100} w={TW} />
            </div>
          );
        })}
      </AbsoluteFill>

      {/* the wavefront */}
      {wave > 0 && wave < 1 &&
        [-1, 1].map((s) => (
          <div
            key={s}
            style={{
              position: "absolute",
              left: wx + s * half - 2,
              top: 0,
              width: 4,
              height: H,
              background: APP.orange,
              opacity: (1 - wave) * 0.9,
              boxShadow: `0 0 40px 10px rgba(242,106,61,${0.35 * (1 - wave)})`,
            }}
          />
        ))}

      {/* ignition glow */}
      <Img
        src={staticFile("fx/glow-orange.png")}
        style={{ position: "absolute", left: wx - 260, top: -160, width: 520, height: 1400, opacity: ignite * 0.55 }}
      />

      {/* the edge -> the tile -> the lockup */}
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: `scale(${hold})`, transformOrigin: "50% 50%" }}>
        <div
          style={{
            position: "absolute",
            left: shape.cx - shape.w / 2,
            top: shape.cy - shape.h / 2,
            width: shape.w,
            height: shape.h,
            borderRadius: radius,
            background: color,
            boxShadow: `0 0 ${(18 * ignite).toFixed(1)}px ${(6 * ignite).toFixed(1)}px rgba(255,190,160,${(0.8 * ignite).toFixed(3)})`,
          }}
        >
          {shape.w > TILE * 0.6 && (
            <div style={{ position: "absolute", left: (shape.w - Math.min(shape.w, shape.h)) / 2, top: (shape.h - Math.min(shape.w, shape.h)) / 2 }}>
              <MarkA size={Math.min(shape.w, shape.h)} p={aP} />
            </div>
          )}
        </div>
        <div style={{ position: "absolute", left: shape.cx - TILE / 2, top: H / 2 - TILE / 2 }}>
          <Wordmark tile={TILE} reveal={reveal} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
