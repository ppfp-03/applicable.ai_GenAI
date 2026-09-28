import React from "react";
import { FONT, VOID } from "../brand/tokens";
import { clamp, mix } from "../lib/anim";
import {
  ageLabel,
  ageOf,
  applicantsAt,
  CARD,
  dayAt,
  fadeWithAge,
  laneTop,
  LAYERS,
  leftX,
  MARKET,
  NOW_X,
  Posting,
} from "./market";

const OVER = 3000; // generous clip bounds so the camera can pull far back

const Chip: React.FC<{ children: React.ReactNode; tone?: "plain" | "warn" | "closed" }> = ({ children, tone = "plain" }) => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      height: 24,
      padding: "0 9px",
      borderRadius: 12,
      fontSize: 13.5,
      fontWeight: 600,
      background: tone === "warn" ? "#3A2A10" : tone === "closed" ? "transparent" : "#262930",
      color: tone === "warn" ? "#F2B455" : tone === "closed" ? VOID.ink3 : VOID.ink2,
      border: tone === "closed" ? `1px dashed ${VOID.line}` : undefined,
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </span>
);

/** A posting as the market shows it: name, place, age, crowd, deadline. */
export const MiniCard: React.FC<{ p: Posting; age: number; x: number; y: number; highlight?: number }> = ({
  p,
  age,
  x,
  y,
  highlight = 0,
}) => {
  const applicants = applicantsAt(p, age);
  const left = p.closeIn - age;
  const closed = left <= 0;
  const fade = fadeWithAge(age);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: CARD.w,
        height: CARD.h,
        borderRadius: 14,
        background: closed ? VOID.card2 : age < 1 ? "#21242B" : VOID.card,
        boxShadow: highlight > 0 ? `0 0 0 ${2 * highlight}px rgba(242,180,85,${0.55 * highlight})` : `inset 0 0 0 1px ${VOID.line}`,
        fontFamily: FONT.board,
        color: VOID.ink,
        opacity: closed ? fade * 0.55 : fade,
        padding: "13px 14px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", gap: 11, alignItems: "center" }}>
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: 7,
            background: "#30343C",
            color: VOID.ink,
            fontSize: 11.5,
            fontWeight: 700,
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          {p.mono}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 16.5, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", width: 196 }}>
            {p.title}
          </div>
          <div style={{ fontSize: 13.5, color: VOID.ink2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", width: 196 }}>
            {p.company} · {p.city}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
        <Chip>{ageLabel(age)}</Chip>
        {closed ? (
          <Chip tone="closed">Closed</Chip>
        ) : (
          <Chip tone={applicants >= 100 ? "warn" : "plain"}>{applicants >= 100 ? "100+ applicants" : `${applicants} applicants`}</Chip>
        )}
      </div>
    </div>
  );
};

/**
 * The market at frame f, in world coordinates (the now edge at NOW_X). Two layers: the front lanes
 * and a deep layer (scaled, darker, defocused) that makes the market read as endless.
 * `emergeAll` (0..1) fades the whole river in; `heroHighlight` rings the posting from Act 1.
 */
export const River: React.FC<{ f: number; opacity?: number; heroHighlight?: number; hideHero?: boolean; day?: number }> = ({
  f,
  opacity = 1,
  heroHighlight = 0,
  hideHero = false,
  day,
}) => {
  const D = day ?? dayAt(f);
  return (
    <div style={{ position: "absolute", inset: 0, opacity }}>
      {([1, 0] as const).map((layer) => {
        const L = LAYERS[layer];
        const cards = MARKET.filter((p) => p.layer === layer).map((p) => {
          const age = ageOf(p, D);
          if (age <= 0) return null;
          const x = leftX(age);
          // cull outside the frame (in the layer's own coordinates)
          const minX = layer === 0 ? -CARD.w - 40 : NOW_X - (NOW_X + CARD.w + 80) / L.scale;
          if (x < minX) return null;
          if (hideHero && p.hero) return null;
          return (
            <MiniCard key={p.id} p={p} age={age} x={x} y={laneTop(layer, p.lane)} highlight={p.hero ? heroHighlight : 0} />
          );
        });
        return (
          // nothing exists in the future: the river is cut at the now edge
          <div
            key={layer}
            style={{ position: "absolute", left: -OVER, top: -OVER, width: NOW_X + OVER, height: 1080 + 2 * OVER, overflow: "hidden" }}
          >
            <div
              style={{
                position: "absolute",
                left: OVER,
                top: OVER,
                width: 1920,
                height: 1080,
                transformOrigin: `${NOW_X}px 540px`,
                transform: layer === 1 ? `scale(${L.scale})` : undefined,
                filter: layer === 1 ? "blur(2.2px) brightness(0.62)" : undefined,
              }}
            >
              {cards}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/** The now edge: a hairline of light with its label. `glow` 0..1 intensifies it. */
export const NowEdge: React.FC<{ x: number; top?: number; bottom?: number; glow?: number; label?: number; color?: string }> = ({
  x,
  top = 70,
  bottom = 1010,
  glow = 0,
  label = 1,
  color = VOID.now,
}) => (
  <>
    <div
      style={{
        position: "absolute",
        left: x - 1.5,
        top,
        width: 3,
        height: bottom - top,
        background: color,
        opacity: mix(0.55, 1, clamp(glow)),
        borderRadius: 2,
      }}
    />
    {label > 0 && (
      <div
        style={{
          position: "absolute",
          left: x + 14,
          top: top - 4,
          fontFamily: FONT.board,
          fontSize: 17,
          fontWeight: 700,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color,
          opacity: label * mix(0.7, 1, clamp(glow)),
        }}
      >
        Now
      </div>
    )}
  </>
);

