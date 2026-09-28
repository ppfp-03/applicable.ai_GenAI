// Two worlds, two palettes.
//
// APP is Applicable.ai as it ships today (ui/css/base.css + ui/palette.py, design-system/assets):
// Inter on a cool paper ground with warm peach glows, one orange accent, green / amber for rule
// outcomes. Colour always means something.
//
// BOARD is the fictional generic job board of the opening: greyscale and flat. It is deliberately
// not LinkedIn (no blue, no name, no logo) and shares nothing with Applicable.ai except that it is
// a familiar web page. VOID is the market seen from far away: the same board cards in the dark.

export const APP = {
  bg: "#F5F6F8",
  surface: "#FFFFFF",
  ink: "#1D1D1F",
  ink2: "#6E6E73",
  ink3: "#8E8E93",
  line: "#E5E5EA",
  line2: "#EFEFF2",
  orange: "#F26A3D", // brand / accent (mockup blue, mapped by ui/palette.py)
  orange2: "#F6915F",
  orange3: "#FAC0A3",
  orange4: "#FDDFD0",
  orangeBg: "#FFEFE7",
  orangeInk: "#B63F16", // ".ai" in the lockup, orange text on light
  tile: "#E1663B", // the mark's tile (never recoloured)
  cream: "#F3EDE3", // the mark's "A"
  green: "#248A3D",
  greenBg: "#EAF6EC",
  amber: "#B25E09",
  amberBg: "#FDF3E4",
  mono: "#1D1D1F", // company monogram tiles
};

export const BOARD = {
  bg: "#ECEEF1",
  surface: "#FFFFFF",
  ink: "#16181D",
  ink2: "#5B616B",
  ink3: "#8A9099",
  line: "#DADDE2",
  chip: "#EEF0F3",
  action: "#262A31", // charcoal buttons
  fresh: "#1E7B45", // "Just posted"
  warn: "#9A5B00", // crowded
  warnBg: "#FFF1D6",
};

export const VOID = {
  bg: "#0D0E11",
  card: "#1A1C21",
  card2: "#15171B",
  line: "#2A2D34",
  ink: "#D4D7DD",
  ink2: "#8B909A",
  ink3: "#5E636C",
  now: "#E9EBEF", // the now edge before it becomes Applicable.ai orange
};

export const FONT = {
  app: '"Inter", system-ui, sans-serif', // the product and the film's voice
  board: '"Figtree", system-ui, sans-serif', // the generic board
};

// Title-safe area for 1920x1080 (key text stays inside).
export const SAFE = { x: 150, y: 110 };
