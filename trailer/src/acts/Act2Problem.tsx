import React, { useMemo } from "react";
import { AbsoluteFill, Easing, Img, staticFile, useCurrentFrame } from "remotion";
import { FONT, SAFE, VOID } from "../brand/tokens";
import { Camera, Cam, drift } from "../fx/Camera";
import { Words } from "../fx/Words";
import { E, mix, prog } from "../lib/anim";
import { fitLines } from "../lib/measure";
import { NowEdge, River } from "../jobboard/River";
import { NOW_X } from "../jobboard/market";
import { ACT, CUE, H, W } from "../timeline";
import { COPY } from "../copy";

// ACT 2 - THE REAL PROBLEM (0:06-0:10)
// The market as a river of time. Every posting enters at the now edge and drifts away from it,
// collecting applicants and losing deadline; time keeps accelerating. Finding is not the problem:
// the distance from now is. The camera ends by rushing the now edge, which becomes the reveal.

const A = ACT.problem.from;
// The rush runs through the act seam and is caught by the reveal (Act 3 keeps this camera).
export const RUSH = { from: CUE.rush, to: ACT.reveal.from + 24, s: 2.05 };
export const RUSH_EASE = Easing.bezier(0.62, 0, 0.3, 1);

export const act2Camera = (f: number): Cam => {
  const d = drift(f, "a2", 3);
  const settle = prog(f, CUE.pullBack + 60, CUE.rush, E.smooth);
  const base: Cam = { x: mix(960, 1010, settle) + d.dx, y: 540 + d.dy, s: mix(1, 1.07, settle) };
  const r = prog(f, RUSH.from, RUSH.to, RUSH_EASE);
  return { x: mix(base.x, NOW_X, r), y: mix(base.y, 540, r), s: mix(base.s, RUSH.s, r) };
};

export const Act2Problem: React.FC = () => {
  const f = useCurrentFrame() + A; // absolute frame
  const cam = act2Camera(f);

  const size1 = useMemo(() => fitLines(["Finding opportunities", "isn’t enough."], W - 2 * SAFE.x - 60, { size: 128, weight: 800, track: -0.045 }), []);
  const size2 = useMemo(() => fitLines(["Timing is the edge."], W - 2 * SAFE.x - 60, { size: 150, weight: 800, track: -0.045 }), []);

  const l1 = prog(f, CUE.line1 - 6, CUE.line1 + 16, E.smooth) * (1 - prog(f, CUE.line1Out, CUE.line1Out + 16, E.smooth));
  const l2 = prog(f, CUE.line2 - 6, CUE.line2 + 16, E.smooth) * (1 - prog(f, CUE.line2Out, CUE.line2Out + 12, E.smooth));
  const glow = prog(f, CUE.edgeGlow, CUE.edgeGlow + 30, E.out);

  return (
    <AbsoluteFill style={{ background: VOID.bg, overflow: "hidden" }}>
      <Img src={staticFile("fx/void-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      <Camera cam={cam}>
        <River f={f} heroHighlight={1 - prog(f, A, A + 60, E.smooth)} />
        {/* the edge's light: it becomes the one thing worth looking at */}
        <Img
          src={staticFile("fx/glow-white.png")}
          style={{ position: "absolute", left: NOW_X - 320, top: -160, width: 640, height: 1400, opacity: glow * 0.42 }}
        />
        <NowEdge x={NOW_X} glow={glow} />
      </Camera>

      {/* scrim: the headline sits in a pool of shadow, the river keeps moving around it */}
      <Img
        src={staticFile("fx/scrim-dark.png")}
        style={{ position: "absolute", inset: 0, width: W, height: H, opacity: Math.max(l1, l2 * 0.9) }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          width: W,
          top: 540 - size1 * 1.08,
          textAlign: "center",
          fontFamily: FONT.app,
          fontWeight: 800,
          fontSize: size1,
          letterSpacing: "-0.045em",
          lineHeight: 1.08,
          color: "#F4F5F7",
        }}
      >
        <div>
          <Words text={COPY.finding.text} f={f} start={COPY.finding.start} stagger={COPY.finding.stagger} out={CUE.line1Out} />
        </div>
        <div>
          <Words text={COPY.notEnough.text} f={f} start={COPY.notEnough.start} stagger={COPY.notEnough.stagger} out={CUE.line1Out + 3} />
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          width: W,
          top: 540 - size2 * 0.56,
          textAlign: "center",
          fontFamily: FONT.app,
          fontWeight: 800,
          fontSize: size2,
          letterSpacing: "-0.045em",
          lineHeight: 1.08,
          color: "#F4F5F7",
        }}
      >
        <Words
          text={COPY.timing.text}
          f={f}
          start={COPY.timing.start}
          stagger={COPY.timing.stagger}
          out={CUE.line2Out}
          outDur={10}
          wordStyle={(i) => (i === 3 ? { color: mixHex("#F4F5F7", "#FFFFFF", glow) } : {})}
        />
      </div>
    </AbsoluteFill>
  );
};

const mixHex = (a: string, b: string, t: number) => {
  const pa = [1, 3, 5].map((k) => parseInt(a.slice(k, k + 2), 16));
  const pb = [1, 3, 5].map((k) => parseInt(b.slice(k, k + 2), 16));
  return `rgb(${pa.map((v, k) => Math.round(mix(v, pb[k], t))).join(",")})`;
};
