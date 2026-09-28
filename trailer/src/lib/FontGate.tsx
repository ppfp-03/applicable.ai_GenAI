import { loadFont } from "@remotion/fonts";
import React, { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

// The film's faces, copied from the product (static/, design-system/fonts/). Both are OFL.
// Inter is the variable face the app ships; Figtree plays the generic job board.
const LATIN_EXT =
  "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF";

let fontsReady: Promise<void> | null = null;

const loadAll = () => {
  fontsReady ??= Promise.all([
    loadFont({ family: "Inter", url: staticFile("fonts/inter-latin-wght-normal.woff2"), weight: "100 900", display: "block" }),
    loadFont({
      family: "Inter",
      url: staticFile("fonts/inter-latin-ext-wght-normal.woff2"),
      weight: "100 900",
      display: "block",
      unicodeRange: LATIN_EXT,
    }),
    ...[400, 500, 600, 700].map((w) =>
      loadFont({ family: "Figtree", url: staticFile(`fonts/figtree-latin-${w}-normal.woff2`), weight: String(w), display: "block" }),
    ),
  ])
    // Force-decode the exact faces the film draws so the first frame never shows a fallback.
    .then(() => Promise.all(["400", "500", "600", "700", "800"].map((w) => document.fonts.load(`${w} 40px "Inter"`))))
    .then(() => Promise.all(["400", "600", "700"].map((w) => document.fonts.load(`${w} 40px "Figtree"`))))
    .then(() => document.fonts.ready)
    .then(() => undefined);
  return fontsReady;
};

/**
 * Renders nothing until every face is loaded and decoded, so no frame ever captures a fallback
 * font and text measurements (lib/measure.ts) are always taken with the real metrics.
 */
export const FontGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [handle] = useState(() => delayRender("Loading brand fonts"));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    loadAll().then(() => {
      setReady(true);
      requestAnimationFrame(() => continueRender(handle));
    });
  }, [handle]);
  return ready ? <>{children}</> : null;
};
