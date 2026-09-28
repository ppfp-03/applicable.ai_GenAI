import React from "react";
import { BOARD, FONT } from "../brand/tokens";

// A fictional, generic professional job board. It borrows the cultural shape of a jobs page
// (search, a results list, a detail pane, an applicant count) and nothing else: no name, no logo,
// no blue. Laid out in page coordinates (1920x1080); acts/Act1TooLate.tsx films it.

export const PANE = { x: 640, y: 104, w: 1160, h: 1100, pad: 64 };
export const HERO = {
  mono: { x: PANE.x + PANE.pad, y: PANE.y + 56, s: 84 },
  title: { x: PANE.x + PANE.pad, y: PANE.y + 172 },
  meta: { x: PANE.x + PANE.pad, y: PANE.y + 252 },
  chips: { x: PANE.x + PANE.pad, y: PANE.y + 312 },
  meter: { x: PANE.x + PANE.pad, y: PANE.y + 392 },
  buttons: { x: PANE.x + PANE.pad, y: PANE.y + 518 },
  about: { x: PANE.x + PANE.pad, y: PANE.y + 632 },
};
export const SAVE_BTN = { x: HERO.buttons.x + 192, y: HERO.buttons.y, w: 150, h: 58 };

export const BoardMono: React.FC<{ text: string; size: number; dark?: boolean }> = ({ text, size, dark = true }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.2,
      background: dark ? BOARD.action : "#C9CDD3",
      color: "#fff",
      display: "grid",
      placeItems: "center",
      fontFamily: FONT.board,
      fontWeight: 700,
      fontSize: size * 0.34,
      letterSpacing: "0.02em",
      flexShrink: 0,
    }}
  >
    {text}
  </div>
);

const Glyph: React.FC = () => (
  <div style={{ width: 44, height: 44, borderRadius: 11, background: BOARD.action, position: "relative" }}>
    <div style={{ position: "absolute", left: 11, top: 13, width: 22, height: 5, borderRadius: 3, background: "#fff" }} />
    <div style={{ position: "absolute", left: 11, top: 22, width: 14, height: 5, borderRadius: 3, background: "#fff", opacity: 0.7 }} />
  </div>
);

export const ClockIcon: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
    <circle cx="12" cy="12" r="9" fill="none" stroke={color} strokeWidth="2.2" />
    <path d="M12 7v5.2l3.4 2" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
  </svg>
);

export const PeopleIcon: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
    <circle cx="9" cy="8.5" r="3.6" fill={color} />
    <path d="M2.5 19.5c.6-3.6 3.3-5.6 6.5-5.6s5.9 2 6.5 5.6z" fill={color} />
    <circle cx="16.8" cy="9.4" r="2.9" fill={color} opacity=".55" />
    <path d="M15.2 14.3c3.3-.5 5.7 1.3 6.3 4.7h-4.3c-.3-1.8-1-3.4-2-4.7z" fill={color} opacity=".55" />
  </svg>
);

const RESULTS = [
  { mono: "LZ", title: "Investment Banking Summer Analyst", co: "Lazarde & Co.", place: "London", hero: true },
  { mono: "MS", title: "Summer Analyst · Global Markets", co: "Morgan Stanfield", place: "London", age: "5 days ago" },
  { mono: "UC", title: "Off-cycle Intern · DCM", co: "UniCreda", place: "Milan", age: "1 week ago" },
  { mono: "DB", title: "Graduate Analyst · Credit", co: "Deutsch Bank", place: "Frankfurt", age: "2 weeks ago" },
  { mono: "BC", title: "Consulting Summer Intern", co: "Bolton Consulting Group", place: "London", age: "2 weeks ago" },
  { mono: "MB", title: "Equity Research Intern", co: "Mediobanco", place: "Milan", age: "3 weeks ago" },
];

/** The page chrome and results list. The hero detail pane is rendered separately (it animates). */
export const BoardChrome: React.FC<{ heroAge: string }> = ({ heroAge }) => (
  <div style={{ position: "absolute", inset: 0, fontFamily: FONT.board, color: BOARD.ink }}>
    {/* top bar */}
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: 1920,
        height: 80,
        background: BOARD.surface,
        borderBottom: `1px solid ${BOARD.line}`,
        display: "flex",
        alignItems: "center",
        padding: "0 120px",
        boxSizing: "border-box",
        gap: 28,
      }}
    >
      <Glyph />
      <div
        style={{
          width: 560,
          height: 48,
          borderRadius: 24,
          background: BOARD.chip,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "0 22px",
          fontSize: 20,
          color: BOARD.ink2,
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24">
          <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke={BOARD.ink2} strokeWidth="2.4" />
          <path d="M15.5 15.5l5 5" stroke={BOARD.ink2} strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <span style={{ color: BOARD.ink, fontWeight: 600 }}>Investment banking</span>
        <span>·</span>
        <span>London</span>
      </div>
      <div style={{ flex: 1 }} />
      {["Home", "Jobs", "Network", "Messages"].map((t) => (
        <div
          key={t}
          style={{
            fontSize: 19,
            fontWeight: t === "Jobs" ? 700 : 500,
            color: t === "Jobs" ? BOARD.ink : BOARD.ink2,
            height: 80,
            display: "flex",
            alignItems: "center",
            boxShadow: t === "Jobs" ? `inset 0 -3px 0 ${BOARD.action}` : undefined,
          }}
        >
          {t}
        </div>
      ))}
      <div style={{ width: 44, height: 44, borderRadius: 22, background: "#C9CDD3" }} />
    </div>

    {/* results list */}
    <div style={{ position: "absolute", left: 120, top: 104, width: 496, height: 1100 }}>
      <div style={{ fontSize: 24, fontWeight: 700, padding: "8px 4px 2px" }}>Jobs for you</div>
      <div style={{ fontSize: 18, color: BOARD.ink2, padding: "0 4px 18px" }}>1,284 results · London</div>
      {RESULTS.map((r, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            gap: 18,
            padding: "22px 20px",
            borderRadius: 14,
            background: r.hero ? BOARD.surface : "transparent",
            boxShadow: r.hero ? `inset 4px 0 0 ${BOARD.action}, 0 1px 3px rgba(0,0,0,0.06)` : undefined,
            borderBottom: r.hero ? undefined : `1px solid ${BOARD.line}`,
            marginBottom: 6,
          }}
        >
          <BoardMono text={r.mono} size={56} dark={!!r.hero} />
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontSize: 21,
                fontWeight: 700,
                lineHeight: 1.25,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                width: 380,
              }}
            >
              {r.title}
            </div>
            <div style={{ fontSize: 18, color: BOARD.ink2, marginTop: 4 }}>
              {r.co} · {r.place}
            </div>
            <div style={{ fontSize: 16, color: BOARD.ink3, marginTop: 6 }}>{r.hero ? heroAge : r.age}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
);
