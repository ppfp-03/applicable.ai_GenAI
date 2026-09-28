import React from "react";
import { BOARD, FONT } from "../brand/tokens";
import { hitPulse, mix, prog, E } from "../lib/anim";
import { AGES, ageAt, arrivalFrame, countAt, HUNDRED, METER, SPILL } from "../acts/act1-data";
import { BoardMono, ClockIcon, HERO, PANE, PeopleIcon } from "./BoardPage";
import { rand } from "../lib/anim";

// The posting's detail pane: the one job you are about to find, three days too late.
// Chip widths are fixed so the row never jumps while the labels change.
export const AGE_CHIP = { w: 262, h: 54 };
export const APPLICANT_CHIP = { x: HERO.chips.x + AGE_CHIP.w + 14, y: HERO.chips.y, w: 318, h: 54 };

const RollLabel: React.FC<{ f: number; labels: { f: number; label: string }[] }> = ({ f, labels }) => {
  const i = ageAt(f);
  const t = i === 0 ? 1 : prog(f, labels[i].f, labels[i].f + 10, E.out);
  const prev = i > 0 ? labels[i - 1].label : null;
  return (
    <span style={{ position: "relative", display: "inline-block", width: 190, height: 30, overflow: "hidden", verticalAlign: "top" }}>
      {prev && t < 1 && (
        <span style={{ position: "absolute", left: 0, top: 0, transform: `translateY(${-t * 30}px)`, opacity: 1 - t, whiteSpace: "nowrap" }}>
          {prev}
        </span>
      )}
      <span style={{ display: "inline-block", transform: `translateY(${(1 - t) * 30}px)`, opacity: prev ? t : 1, whiteSpace: "nowrap" }}>
        {labels[i].label}
      </span>
    </span>
  );
};

/** One seat in the applicant meter. It fills with a small pop when its applicant arrives. */
const Seat: React.FC<{ i: number; f: number; hot: number }> = ({ i, f, hot }) => {
  const col = Math.floor(i / METER.rows);
  const row = i % METER.rows;
  const at = arrivalFrame(i + 1);
  const p = prog(f, at, at + 7, E.out);
  const pop = hitPulse(f - at, 1.5, 3) * 0.35;
  const x = col * (METER.dot + METER.gap);
  const y = row * (METER.dot + METER.gap);
  return (
    <>
      <div style={{ position: "absolute", left: x, top: y, width: METER.dot, height: METER.dot, borderRadius: 7, background: "#E3E6EA" }} />
      {p > 0 && (
        <div
          style={{
            position: "absolute",
            left: x,
            top: y,
            width: METER.dot,
            height: METER.dot,
            borderRadius: 7,
            background: hot > 0 ? mixColor(BOARD.action, "#C77A0A", hot) : BOARD.action,
            transform: `scale(${(p + pop).toFixed(4)})`,
          }}
        />
      )}
    </>
  );
};

const mixColor = (a: string, b: string, t: number) => {
  const pa = [1, 3, 5].map((k) => parseInt(a.slice(k, k + 2), 16));
  const pb = [1, 3, 5].map((k) => parseInt(b.slice(k, k + 2), 16));
  return `rgb(${pa.map((v, k) => Math.round(mix(v, pb[k], t))).join(",")})`;
};

/** Applicants who arrive after the meter is full: they spill out of it and fall off the card. */
const Spill: React.FC<{ f: number }> = ({ f }) => {
  if (f < HUNDRED || f > HUNDRED + 40) return null;
  const w = METER.cols * (METER.dot + METER.gap) - METER.gap;
  return (
    <>
      {Array.from({ length: SPILL }, (_, k) => {
        const t0 = HUNDRED + k * 1.6;
        const t = (f - t0) / 60; // seconds
        if (t <= 0) return null;
        const vx = 70 + rand(`sp${k}`) * 170; // px/s: they pour off the meter's end
        const vy = -160 - rand(`sv${k}`) * 140;
        const g = 3200;
        const x = w + 6 + vx * t;
        const y = (k % METER.rows) * (METER.dot + METER.gap) + vy * t + 0.5 * g * t * t;
        if (y > 700) return null;
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: METER.dot,
              height: METER.dot,
              borderRadius: 7,
              background: "#C77A0A",
              opacity: Math.min(1, t * 12) * Math.max(0, 1 - Math.max(0, t - 0.3) / 0.25),
            }}
          />
        );
      })}
    </>
  );
};

export const HeroPane: React.FC<{ f: number; saved: number; press: number }> = ({ f, saved, press }) => {
  const n = countAt(f);
  const hot = prog(f, HUNDRED, HUNDRED + 6, E.out);
  const kick = hitPulse(f - HUNDRED, 2, 7);
  const label = n >= 100 ? "100+ applicants" : n === 0 ? "No applicants yet" : `${n} applicant${n === 1 ? "" : "s"}`;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: PANE.w,
        height: PANE.h,
        background: BOARD.surface,
        borderRadius: 18,
        boxShadow: "0 1px 3px rgba(20,24,30,0.06), 0 10px 30px rgba(20,24,30,0.05)",
        fontFamily: FONT.board,
        color: BOARD.ink,
      }}
    >
      {/* coordinates below are relative to the pane */}
      <div style={{ position: "absolute", left: PANE.pad, top: HERO.mono.y - PANE.y, display: "flex", gap: 22, alignItems: "center" }}>
        <BoardMono text="LZ" size={HERO.mono.s} />
        <div>
          <div style={{ fontSize: 27, fontWeight: 700 }}>Lazarde & Co.</div>
          <div style={{ fontSize: 20, color: BOARD.ink2, marginTop: 4 }}>Investment banking · 2,400 employees</div>
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: PANE.pad,
          top: HERO.title.y - PANE.y,
          fontSize: 56,
          fontWeight: 700,
          letterSpacing: "-0.02em",
          whiteSpace: "nowrap",
          lineHeight: 1.1,
        }}
      >
        Investment Banking Summer Analyst
      </div>
      <div style={{ position: "absolute", left: PANE.pad, top: HERO.meta.y - PANE.y, fontSize: 24, color: BOARD.ink2 }}>
        London, United Kingdom · Internship · Summer 2027
      </div>

      {/* age + applicants */}
      <div style={{ position: "absolute", left: PANE.pad, top: HERO.chips.y - PANE.y, display: "flex", gap: 14 }}>
        <div
          style={{
            width: AGE_CHIP.w,
            height: AGE_CHIP.h,
            borderRadius: 27,
            background: BOARD.chip,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "0 20px",
            boxSizing: "border-box",
            fontSize: 23,
            fontWeight: 600,
            color: f < AGES[1].f ? BOARD.fresh : BOARD.ink2,
          }}
        >
          <ClockIcon size={24} color={f < AGES[1].f ? BOARD.fresh : BOARD.ink2} />
          <RollLabel f={f} labels={AGES} />
        </div>
        <div
          style={{
            width: APPLICANT_CHIP.w,
            height: APPLICANT_CHIP.h,
            borderRadius: 27,
            background: hot > 0 ? mixColor(BOARD.chip, BOARD.warnBg, hot) : BOARD.chip,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "0 20px",
            boxSizing: "border-box",
            fontSize: 23,
            fontWeight: 700,
            color: hot > 0 ? mixColor(BOARD.ink, BOARD.warn, hot) : BOARD.ink,
            fontVariantNumeric: "tabular-nums",
            transform: `scale(${1 + kick * 0.09})`,
            transformOrigin: "30% 50%",
          }}
        >
          <PeopleIcon size={26} color={hot > 0 ? mixColor(BOARD.ink2, BOARD.warn, hot) : BOARD.ink2} />
          <span style={{ whiteSpace: "nowrap" }}>{label}</span>
        </div>
      </div>

      {/* the applicant meter: one seat per applicant, a hundred seats */}
      <div style={{ position: "absolute", left: PANE.pad, top: HERO.meter.y - PANE.y }}>
        {Array.from({ length: METER.cols * METER.rows }, (_, i) => (
          <Seat key={i} i={i} f={f} hot={hot} />
        ))}
        <Spill f={f} />
      </div>

      {/* actions */}
      <div style={{ position: "absolute", left: PANE.pad, top: HERO.buttons.y - PANE.y, display: "flex", gap: 20 }}>
        <div
          style={{
            width: 172,
            height: 58,
            borderRadius: 29,
            background: BOARD.action,
            color: "#fff",
            display: "grid",
            placeItems: "center",
            fontSize: 23,
            fontWeight: 700,
          }}
        >
          Apply
        </div>
        <div
          style={{
            width: 150,
            height: 58,
            borderRadius: 29,
            border: `2px solid ${BOARD.action}`,
            boxSizing: "border-box",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            fontSize: 23,
            fontWeight: 700,
            background: saved > 0 ? `rgba(38,42,49,${0.08 * saved})` : undefined,
            transform: `scale(${1 - press * 0.05})`,
          }}
        >
          <svg width="18" height="22" viewBox="0 0 18 22">
            <path
              d="M2 2h14v18l-7-5-7 5z"
              fill={saved > 0.5 ? BOARD.action : "none"}
              stroke={BOARD.action}
              strokeWidth="2.4"
              strokeLinejoin="round"
            />
          </svg>
          {saved > 0.5 ? "Saved" : "Save"}
        </div>
      </div>

      {/* about */}
      <div style={{ position: "absolute", left: PANE.pad, top: HERO.about.y - PANE.y, width: PANE.w - 2 * PANE.pad }}>
        <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 14 }}>About the job</div>
        <div style={{ fontSize: 22, lineHeight: 1.6, color: BOARD.ink2 }}>
          Join our London advisory team for ten weeks next summer. You will work on live M&amp;A mandates, build
          valuation models and support client pitches alongside senior bankers. Strong candidates will have a
          finance background and a genuine interest in how companies grow, merge and raise capital.
        </div>
      </div>
    </div>
  );
};

export const PANE_RECT = { x: PANE.x, y: PANE.y, w: PANE.w, h: PANE.h };
export { mixColor };
