import React from "react";
import { APP } from "./tokens";
import { MARK_A, MARK_TILE_RX, WORD_AI, WORD_APPLICABLE } from "./logoPaths";

// The Applicable.ai mark and lockup, drawn from the official outlines (brand/logoPaths.ts).
// The tile is a DOM box so it can morph to and from the film's other shapes (the now line, the
// top-ranked row); the "A" and the wordmark are the exact SVG outlines laid over it.

export const TILE_RADIUS = MARK_TILE_RX / 100; // corner radius as a fraction of the tile side

/** The cream "A", in the tile's 100x100 space. `p` 0..1 reveals it rising out of the tile. */
export const MarkA: React.FC<{ size: number; p: number }> = ({ size, p }) => {
  if (p <= 0) return null;
  const lift = (1 - p) * 26; // units: the A rises into place from inside the tile
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      style={{ position: "absolute", left: 0, top: 0, overflow: "hidden", borderRadius: size * TILE_RADIUS }}
    >
      <g transform={`translate(0 ${lift})`} opacity={Math.min(1, p * 1.6)}>
        <path d={MARK_A} fill={APP.cream} />
      </g>
    </svg>
  );
};

/**
 * The wordmark, emerging from behind the tile's right edge. Positioned relative to a tile whose
 * top-left is (0,0) and side is `tile` px, exactly as in applicable-lockup.svg.
 * `reveal` 0..1 slides it out; the clip starts at the tile's edge so it is never seen overlapping.
 */
export const Wordmark: React.FC<{ tile: number; reveal: number; ink?: string; ai?: string }> = ({
  tile,
  reveal,
  ink = APP.ink,
  ai = APP.orangeInk,
}) => {
  if (reveal <= 0) return null;
  const u = tile / 40; // px per lockup unit (the tile is 40 units wide)
  const clipLeft = 41 * u;
  const width = 242 * u - clipLeft;
  const slide = (1 - reveal) * (width + 4 * u);
  return (
    <div style={{ position: "absolute", left: clipLeft, top: -4 * u, width, height: 48 * u, overflow: "hidden", opacity: Math.min(1, reveal * 1.8) }}>
      <svg
        width={242 * u}
        height={48 * u}
        viewBox="0 0 242 48"
        style={{ position: "absolute", left: -clipLeft - slide, top: 0 }}
      >
        <path d={WORD_APPLICABLE} fill={ink} />
        <path d={WORD_AI} fill={ai} />
      </svg>
    </div>
  );
};

/** Width in px of the full lockup for a tile of `tile` px. */
export const lockupWidth = (tile: number) => (239.5 / 40) * tile;
