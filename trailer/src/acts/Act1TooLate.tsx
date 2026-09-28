import React, { useMemo } from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { BOARD, FONT, SAFE } from "../brand/tokens";
import { Camera, Cam, drift } from "../fx/Camera";
import { Words } from "../fx/Words";
import { E, hitPulse, mix, prog, tw } from "../lib/anim";
import { fitLines } from "../lib/measure";
import { BoardChrome, PANE, SAVE_BTN } from "../jobboard/BoardPage";
import { AGES, ageAt, CURSOR, HUNDRED, PUNCH } from "./act1-data";
import { APPLICANT_CHIP, HeroPane } from "../jobboard/HeroPane";
import { MiniCard, NowEdge, River } from "../jobboard/River";
import { CARD, dayAt, HERO_ID, laneTop, leftX, MARKET, NOW_X } from "../jobboard/market";
import { ACT, CUE, H, W } from "../timeline";
import { COPY } from "../copy";

// ACT 1 - TOO LATE (0:00-0:06)
// A job board, one great posting. Its age label ticks forward on the beat while its applicants
// arrive and fill a hundred seats. On the downbeat the meter overflows: 100+. You arrive, you save
// it. "You found it." "So did everyone else." Then the posting shrinks into the market it belongs
// to, already drifting away from now.

const hero = MARKET.find((p) => p.id === HERO_ID)!;
const ACT_END = ACT.tooLate.from + ACT.tooLate.dur;

// the applicants chip in page coordinates (the punch-in target)
const CHIP_C = { x: APPLICANT_CHIP.x + APPLICANT_CHIP.w / 2, y: APPLICANT_CHIP.y + APPLICANT_CHIP.h / 2 + 50 };

export const cameraAt = (f: number): Cam => {
  const d = drift(f, "a1", 2.5);
  // opening: close on the posting, easing back as the time-lapse runs
  const open = prog(f, 0, HUNDRED - 6, E.smooth);
  let cam: Cam = { x: mix(1190, 1170, open) + d.dx, y: mix(470, 520, open) + d.dy, s: mix(1.46, 1.2, open) };
  // 100+: punch in on the count, hold, then pull out to the whole page
  const pin = prog(f, PUNCH.at, PUNCH.at + PUNCH.in, E.out);
  const pout = prog(f, PUNCH.holdTo, PUNCH.outTo, E.cam);
  if (f >= PUNCH.at) {
    const punch: Cam = { x: CHIP_C.x + d.dx * 0.4, y: CHIP_C.y + d.dy * 0.4, s: 2.2 + tw(f, PUNCH.at, PUNCH.holdTo, 0, 0.05, E.linear) };
    const wide: Cam = {
      x: 960 + d.dx,
      y: 560 + d.dy,
      s: tw(f, PUNCH.outTo, CUE.pullBack, 1, 0.97, E.smooth) * tw(f, CUE.pullBack, CUE.pullBack + 44, 1, 0.52, E.in),
    };
    cam = {
      x: mix(mix(cam.x, punch.x, pin), wide.x, pout),
      y: mix(mix(cam.y, punch.y, pin), wide.y, pout),
      s: mix(mix(cam.s, punch.s, pin), wide.s, pout),
    };
  }
  return cam;
};

const toScreen = (cam: Cam, x: number, y: number) => ({ x: W / 2 + (x - cam.x) * cam.s, y: H / 2 + (y - cam.y) * cam.s });

const Cursor: React.FC<{ x: number; y: number; press: number }> = ({ x, y, press }) => (
  <svg
    width="34"
    height="44"
    viewBox="0 0 34 44"
    style={{ position: "absolute", left: x - 4, top: y - 3, transform: `scale(${1 - press * 0.12})`, transformOrigin: "4px 3px" }}
  >
    <path d="M4 3 L4 35 L12.5 27.5 L18 40 L23.5 37.6 L18.2 25.4 L29.5 25.4 Z" fill="#111317" stroke="#fff" strokeWidth="2.6" strokeLinejoin="round" />
  </svg>
);

export const Act1TooLate: React.FC = () => {
  const f = useCurrentFrame();
  const cam = cameraAt(f);

  // you arrive: the cursor glides in and saves the posting
  const cp = prog(f, CURSOR.from, CURSOR.to, E.cam);
  const saveC = { x: SAVE_BTN.x + SAVE_BTN.w / 2 + 10, y: SAVE_BTN.y + SAVE_BTN.h / 2 + 8 };
  const cursor = { x: mix(1720, saveC.x, cp), y: mix(1150, saveC.y, cp) };
  const press = hitPulse(f - CUE.click, 2, 4);
  const saved = prog(f, CUE.click, CUE.click + 4, E.out);

  // rack focus under the headline
  const rack = prog(f, CUE.click + 2, CUE.foundIt + 4, E.out) * 1.35;
  // the 100+ flash: a brief exposure lift on the downbeat
  const flash = hitPulse(f - HUNDRED, 1.5, 5);

  // ---- the pull-back into the market (f300-360) ----
  const pb = prog(f, CUE.pullBack, ACT_END - 4, E.inOut);
  // the lights go down on the page (brightness, not a grey cross-fade), then the market is there
  const dim = prog(f, CUE.pullBack + 20, ACT_END - 2, E.smooth);
  const lightsDown = prog(f, CUE.pullBack + 14, CUE.pullBack + 38, E.inOut);
  const day = dayAt(f);
  const target = { x: leftX(3 + day), y: laneTop(0, hero.lane), w: CARD.w, h: CARD.h };
  const paneScreen = (() => {
    const tl = toScreen(cam, PANE.x, PANE.y);
    return { x: tl.x, y: tl.y, w: PANE.w * cam.s, h: (1080 - PANE.y + 40) * cam.s };
  })();
  const rect = {
    x: mix(paneScreen.x, target.x, pb),
    y: mix(paneScreen.y, target.y, pb),
    w: mix(paneScreen.w, target.w, pb),
    h: mix(paneScreen.h, target.h, pb),
  };
  const toMini = prog(f, CUE.pullBack + 26, ACT_END - 6, E.smooth);
  const paneBlur = Math.min(1, rack) * 9 * (1 - prog(f, CUE.textOut + 16, CUE.textOut + 34, E.smooth));

  // headline sizing: computed so both lines sit inside title-safe at one size
  const size = useMemo(
    () => fitLines(["You found it.", "So did everyone else."], W - 2 * SAFE.x - 40, { size: 136, weight: 800, track: -0.045 }),
    [],
  );

  const heroAge = AGES[ageAt(f)].label;
  // depth of field: the page around the posting is soft until the camera pulls out to the page
  const chromeBlur = 2.6 * (1 - prog(f, PUNCH.holdTo, PUNCH.outTo, E.smooth));
  const lineOut = CUE.textOut;

  return (
    <AbsoluteFill style={{ background: BOARD.bg, overflow: "hidden" }}>
      {/* the market, fading up behind the page as the lights go down */}
      <AbsoluteFill style={{ opacity: dim }}>
        <Img src={staticFile("fx/void-bg.png")} style={{ position: "absolute", inset: 0, width: W, height: H }} />
        <River f={f} opacity={prog(f, CUE.voidIn, ACT_END, E.smooth)} hideHero />
        <NowEdge x={NOW_X} glow={0} label={prog(f, CUE.voidIn + 10, ACT_END, E.smooth)} />
      </AbsoluteFill>

      {/* the board page, filmed */}
      {f < ACT_END && (
        <AbsoluteFill
          style={{
            opacity: 1 - prog(f, CUE.pullBack + 26, ACT_END - 4, E.smooth),
            filter: `${rack > 0.001 ? `blur(${(rack * 7).toFixed(2)}px) ` : ""}brightness(${mix(1, 0.1, lightsDown).toFixed(4)})`,
          }}
        >
          <Camera cam={cam}>
            <div style={{ position: "absolute", inset: 0, filter: chromeBlur > 0.01 ? `blur(${chromeBlur.toFixed(2)}px)` : undefined }}>
              <BoardChrome heroAge={heroAge} />
            </div>
            {f < CUE.pullBack && (
              <div style={{ position: "absolute", left: PANE.x, top: PANE.y }}>
                <HeroPane f={f} saved={saved} press={press} />
              </div>
            )}
          </Camera>
        </AbsoluteFill>
      )}

      {/* the posting itself, shrinking into its place in the market */}
      {f >= CUE.pullBack && (
        <div
          style={{
            position: "absolute",
            left: rect.x,
            top: rect.y,
            width: rect.w,
            height: rect.h,
            borderRadius: mix(18 * cam.s, 14, pb),
            overflow: "hidden",
            background: `rgb(${Math.round(mix(255, 26, toMini))},${Math.round(mix(255, 28, toMini))},${Math.round(mix(255, 33, toMini))})`,
            // stays out of focus until the lines have left, then sharpens as it becomes a card
            filter: `${paneBlur > 0.05 ? `blur(${paneBlur.toFixed(2)}px) ` : ""}brightness(${mix(1, 0.55, lightsDown * (1 - toMini)).toFixed(4)})`,
          }}
        >
          <div style={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", transform: `scale(${rect.w / PANE.w})`, opacity: 1 - toMini }}>
            <HeroPane f={f} saved={1} press={0} />
          </div>
          <div style={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", transform: `scale(${rect.w / CARD.w})`, opacity: toMini }}>
            <MiniCard p={hero} age={3 + day} x={0} y={0} highlight={toMini} />
          </div>
        </div>
      )}

      {/* the cursor (you) */}
      {f >= CURSOR.from && f < CUE.click + 30 && (
        <div style={{ position: "absolute", inset: 0, filter: rack > 0.001 ? `blur(${(rack * 7).toFixed(2)}px)` : undefined, opacity: 1 - prog(f, CUE.click + 10, CUE.click + 30) }}>
          {(() => {
            const s = toScreen(cam, cursor.x, cursor.y);
            return <Cursor x={s.x} y={s.y} press={press} />;
          })()}
        </div>
      )}

      {/* exposure lift on the 100+ downbeat */}
      {flash > 0.01 && <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.22 }} />}

      {/* "You found it." / "So did everyone else." */}
      {f >= CUE.foundIt - 10 && f < ACT_END && (
        <AbsoluteFill>
          <Img
            src={staticFile("fx/scrim-light.png")}
            style={{ position: "absolute", inset: 0, width: W, height: H, opacity: Math.min(1, rack) * (1 - prog(f, lineOut, lineOut + 12, E.smooth)) }}
          />
          <div
            style={{
              position: "absolute",
              left: 0,
              width: W,
              top: 540 - size * 1.12,
              textAlign: "center",
              fontFamily: FONT.app,
              fontWeight: 800,
              fontSize: size,
              letterSpacing: "-0.045em",
              lineHeight: 1.12,
              color: BOARD.ink,
            }}
          >
            <div>
              <Words text={COPY.foundIt.text} f={f} start={COPY.foundIt.start} stagger={COPY.foundIt.stagger} dur={22} out={lineOut} outDur={9} />
            </div>
            <div>
              <Words
                text={COPY.everyone.text}
                f={f}
                start={COPY.everyone.start}
                stagger={COPY.everyone.stagger}
                dur={22}
                out={lineOut + 2}
                outDur={9}
              />
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
