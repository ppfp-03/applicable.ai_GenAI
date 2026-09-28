import React, { useMemo } from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { APP, FONT, SAFE } from "../brand/tokens";
import { lockupWidth, MarkA, TILE_RADIUS, Wordmark } from "../brand/Mark";
import { Camera, drift } from "../fx/Camera";
import { Words } from "../fx/Words";
import { E, mix, prog, SPR, springAt } from "../lib/anim";
import { fitLines } from "../lib/measure";
import { MatchRow, mixHex, ROW } from "../product/ui";
import { ACT, CUE, H, W } from "../timeline";
import { COPY } from "../copy";
import { act5Camera, existingY, heroRect, ListHeader, RowRing } from "./Act5ActFirst";
import { EXISTING, LIST, NEWCOMER } from "./act5-data";

// ACT 6 - COMPETITIVE EDGE (0:25-0:30)
// The noise is gone: one clear first move. The rest of the list steps back, #1 comes to the
// centre, and the top opportunity - wrapped in the now edge - folds into the Applicable.ai tile.
// The line lands above it and the lockup holds.

const A = ACT.edge.from;
export const T6 = 150; // final tile size
export const LOCK6 = { left: W / 2 - lockupWidth(T6) / 2, cy: 668 };
export const R6 = {
  headOut: { from: A, to: A + 16 },
  rest: { from: A + 4, to: A + 50 },
  center: { from: A + 10, to: A + 62 },
  morph: { from: CUE.merge, to: CUE.merge + 40 },
  content: { from: CUE.merge, to: CUE.merge + 14 },
  word: { from: CUE.lockup - 26, to: CUE.lockup + 10 },
};

export const Act6Lockup: React.FC = () => {
  const f = useCurrentFrame() + A;
  const start = act5Camera(A);
  const d = drift(f, "a6", 1.6);
  const settle = prog(f, A, A + 70, E.smooth);
  const cam = { x: mix(start.x, 960, settle) + d.dx, y: mix(start.y, 540, settle) + d.dy, s: mix(start.s, 1, settle) };

  const rest = prog(f, R6.rest.from, R6.rest.to, E.inOut);
  const center = prog(f, R6.center.from, R6.center.to, E.inOut);
  const morph = prog(f, R6.morph.from, R6.morph.to, E.inOut);
  const land = springAt(f - (R6.morph.to - 8), SPR.snap);
  const content = prog(f, R6.content.from, R6.content.to, E.smooth);

  // #1: from its slot to the centre, then row -> tile at the lockup's tile position
  const r0 = heroRect(A);
  const rowCy = mix(r0.y + ROW.h / 2, LOCK6.cy, center);
  const tileCx = LOCK6.left + T6 / 2;
  const sizeK = mix(0.9, 1, land);
  const w = mix(ROW.w, T6 * sizeK + (1 - sizeK) * T6 * 1.1, morph);
  const h = mix(ROW.h, T6 * sizeK + (1 - sizeK) * T6 * 1.1, morph);
  const cx = mix(mix(r0.x + ROW.w / 2, W / 2, center), tileCx, morph);
  const color = mixHex("#FFFFFF", APP.tile, prog(f, R6.morph.from + 6, R6.morph.to - 6, E.smooth));
  const radius = mix(18, Math.min(w, h) * TILE_RADIUS, morph);
  const aP = Math.min(1, springAt(f - CUE.aIn6, SPR.snap));
  const reveal = prog(f, R6.word.from, R6.word.to, E.out);

  const size = useMemo(
    () => fitLines(["Your competitive edge starts with", "knowing where to move first."], W - 2 * SAFE.x - 80, { size: 84, weight: 800, track: -0.04 }),
    [],
  );

  return (
    <AbsoluteFill style={{ background: APP.bg, overflow: "hidden" }}>
      <Img src={staticFile("fx/app-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
      <Camera cam={cam}>
        <ListHeader o={1 - rest} />
        {EXISTING.map((m, i) => (
          <div
            key={m.mono}
            style={{
              position: "absolute",
              left: LIST.x,
              top: existingY(i, A) + rest * (60 + i * 20),
              opacity: 1 - rest,
              filter: rest > 0.01 ? `blur(${(rest * 4).toFixed(2)}px)` : undefined,
            }}
          >
            <MatchRow m={m} rank={i + 2} dim={rest} />
          </div>
        ))}

        {/* the top opportunity, wrapped in the now edge */}
        <div
          style={{
            position: "absolute",
            left: cx - w / 2,
            top: rowCy - h / 2,
            width: w,
            height: h,
            borderRadius: radius,
            background: color,
            overflow: "hidden",
            boxShadow: `0 ${mix(10, 14, morph)}px ${mix(30, 40, morph)}px rgba(64,40,28,${mix(0.1, 0.12, morph)})`,
          }}
        >
          {content < 1 && (
            <div style={{ position: "absolute", left: 0, top: 0, opacity: 1 - content, transformOrigin: "0 0", transform: `scale(${w / ROW.w}, ${h / ROW.h})` }}>
              <MatchRow m={NEWCOMER} rank={1} freshGlow={1} />
            </div>
          )}
          {morph > 0.6 && (
            <div style={{ position: "absolute", left: (w - Math.min(w, h)) / 2, top: (h - Math.min(w, h)) / 2 }}>
              <MarkA size={Math.min(w, h)} p={aP} />
            </div>
          )}
        </div>
        {morph < 0.35 && <RowRing p={1} x={cx - ROW.w / 2 - 4} y={rowCy - ROW.h / 2 - 4} o={1 - morph / 0.35} />}

        {/* the wordmark */}
        <div style={{ position: "absolute", left: LOCK6.left, top: LOCK6.cy - T6 / 2 }}>
          <Wordmark tile={T6} reveal={reveal} />
        </div>
      </Camera>

      {/* the line */}
      <div
        style={{
          position: "absolute",
          left: 0,
          width: W,
          top: 250,
          textAlign: "center",
          fontFamily: FONT.app,
          fontWeight: 800,
          fontSize: size,
          letterSpacing: "-0.04em",
          lineHeight: 1.1,
          color: APP.ink,
        }}
      >
        <div>
          <Words text={COPY.yourEdge.text} f={f} start={COPY.yourEdge.start} stagger={COPY.yourEdge.stagger} dur={22} />
        </div>
        <div>
          <Words text={COPY.knowing.text} f={f} start={COPY.knowing.start} stagger={COPY.knowing.stagger} dur={22} wordStyle={(i) => (i === 4 ? { color: APP.orange } : {})} />
        </div>
      </div>

      {/* Act 5's headline hands over */}
      <HeadlineOut f={f} />
    </AbsoluteFill>
  );
};

const HeadlineOut: React.FC<{ f: number }> = ({ f }) => {
  const size = useMemo(() => fitLines(["Know where to move first."], W - 2 * SAFE.x, { size: 116, weight: 800, track: -0.045 }), []);
  if (f > R6.headOut.to + 20) return null;
  return (
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
      <Words text={COPY.knowWhere.text} f={f} start={-100} stagger={0} dur={1} out={R6.headOut.from} outDur={16} wordStyle={(i) => (i === 4 ? { color: APP.orange } : {})} />
    </div>
  );
};
