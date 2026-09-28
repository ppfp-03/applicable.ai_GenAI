# Applicable.ai - launch film

A 30-second launch film for Applicable.ai, generated entirely from code. The picture is React
rendered by [Remotion](https://www.remotion.dev); the score and every sound effect are synthesized
in Python. No footage, no samples, no stock music, no templates.

- 30.000 s, 1800 frames, 60 fps, 1920x1080, H.264 yuv420p BT.709
- Stereo AAC-LC 320 kb/s, 48 kHz, -14 LUFS integrated, true peak <= -1 dBTP (measured after the encode)
- Final master with temporal motion blur (216 deg shutter), accumulated in float outside the browser

This directory is self-contained. Nothing in the production app is imported or modified; the
fonts and logo outlines were copied from `static/` and `design-system/`.

## The idea

**Space is time.** Every opportunity sits as far from *now* as it is old. The film's one
persistent object is **the now edge**: a vertical line that marks the present.

| Time | Act | What happens |
| --- | --- | --- |
| 0:00 | **Too late** | A posting on a fictional, generic job board. Its age label steps forward on every beat (*Just posted, 20 minutes ago, 1 hour ago ... 3 days ago*) while applicants fill a hundred-seat meter. On the downbeat the meter overflows: **100+ applicants**. You arrive, you save it. *You found it. So did everyone else.* |
| 0:05 | the lights go down | The page recedes into the dark and the posting becomes one card in the market, already three days from the now edge. |
| 0:06 | **The real problem** | The market as a river of time: postings slide out from behind the now edge and drift away from it, collecting applicants and losing deadline. Time accelerates. *Finding opportunities isn't enough.* *Timing is the edge.* - and the edge lights up. The camera rushes it. |
| 0:10 | **Applicable.ai** | The edge ignites in Applicable.ai orange. A wave of order runs out of it: the dark board market becomes the product's light, ranked Explore grid. The edge folds into the Applicable.ai tile, the "A" rises in it and the wordmark slides out. Then the tile unfolds back into the edge: the brand is the thing watching *now*. |
| 0:14 | **Find what's fresh** | Applicable.ai's view of the opportunity set unfolds out of the edge, every role placed by age on an axis labelled *First seen by Applicable.ai*. Older roles sink back one per beat; fresh ones are born at the edge (*2h ago, Today, New*) with a ping. *See what matters while it still matters.* |
| 0:20 | **Act first** | A strong new role is born at the edge: *New, first seen today*. Applicable.ai checks it (*Strong fit, 7 of 8 key skills*; *RULE Eligible under checked rules*). It lifts into **#1 of Your top matches**, the others make room, and the now edge wraps it. *Know where to move first.* |
| 0:25 | **Competitive edge** | The rest of the list steps back. The top opportunity, wrapped in the edge, folds into the tile; the lockup forms under *Your competitive edge starts with knowing where to move first.* and holds for two seconds. |

### Why this metaphor

The team's thesis is that the edge is *timing*. The problem world shows the edge as a thing you
fall away from (every posting drifts from it); Applicable.ai is the moment the edge becomes a tool:
the same line turns orange, becomes the logo, becomes the product's own *Now* marker (the live app
draws one on its "Next two weeks" timeline) and finally becomes the outline around your #1. One
object passes through every act, so the film reads as one continuous relay.

### Visual worlds

- **The board** (0:00-0:06): greyscale, flat, Figtree. Generic on purpose - search, a results list,
  a detail pane, an applicant count. No name, no logo, no blue, nothing borrowed from LinkedIn, and
  nothing that suggests Applicable.ai reads any board.
- **The market** (0:06-0:10): the same cards in the dark, two layers deep (a defocused back layer
  makes it endless). Crowded roles turn amber, closed ones go dashed.
- **Applicable.ai** (0:10-0:30): rebuilt from the shipping app, not the older design-system mockups:
  Inter, `#F5F6F8` with the app's peach and mint glows, one orange, dark monogram tiles, the Explore
  tile and Matches row geometry, the four-factor priority bar, the green *Eligible* dot and the
  *RULE* tag. Tokens are in `src/brand/tokens.ts`, taken from `ui/css/base.css` and `ui/palette.py`.

### Product truth kept on screen

- Applicant counts exist only in the fictional board world. Applicable.ai never shows one.
- Ages in the product world are **discovery times**: the axis says *First seen by Applicable.ai* and
  the new role says *first seen today*. No source publication date is claimed (PROJECT_CONTEXT
  "Data acquisition and freshness"; `FreshnessAssessment` in `src/oi/intelligence/ranking.py`).
- Freshness is one of four factor families. The #1 row keeps the app's stacked bar and legend
  (*Profile, Preference, Deadline urgency, Freshness*): the new role outranks on fit, preferences and
  deadline as well.
- Eligibility is shown the way the product words it (*RULE - Eligible under checked rules*). No
  interview odds, no hiring probability, no auto-apply, no comparison with other candidates.
- Roles and companies are the product's own fictional demo names. Scores are illustrative.
- The product is named only *Applicable.ai*; the optional descriptor was left out because the
  design system forbids descriptors next to the name (`design-system/README.md`, *Naming*).

## Sound

`scripts/soundtrack.py` synthesizes everything from oscillators and noise (PolyBLEP saws, FM bells
and FM electric piano, filtered-noise clicks, whooshes and risers, sub impacts, convolution reverb
from generated impulse responses, sidechain, a bus compressor, saturation and a true-peak limiter).
It reads `out/cues.json`, exported from the same timeline and motion functions as the picture.

- **Time**: a dry wooden tick on every beat while the posting ages, one step higher each time its
  age label changes. It returns, calm and in time, on the last three beats.
- **Competition**: every applicant is a click on the exact frame its seat fills (99 of them). They
  thicken into a crowd murmur that breaks off on the 100+ hit (sub drop + a D-Eb-A cluster).
- **Overload**: D minor that will not settle - detuned, drifting pads over a pushing 16th-note
  bass; every posting that slides out of the now edge ticks, panned to its lane.
- **Detection**: the *edge ping*, an FM bell figure A-D-F#. It sounds when the "A" rises into the
  tile, when a fresh role is born, when the new role lands at #1 and on the final lockup.
- **Arc**: the same root turns from D minor to D major when Applicable.ai appears. Drop 1 is the
  ignition (0:10), drop 2 (the largest) is the landing at #1 (0:22), and the film resolves on D add9.
- 120 BPM: acts land on the grid, but impacts land where the picture lands (spring contact frames,
  velocity peaks of camera moves, seat fills, card births), not merely on the beat.

## Pipeline

```
src/timeline.ts, src/copy.ts ─┬─> picture (Remotion, src/acts/*)
                               └─> scripts/export-cues.ts ─> out/cues.json ─> scripts/soundtrack.py ─> public/audio/soundtrack.wav
preview:  Remotion (sharp) ───────────────────────────────────────┐
final:    Remotion (sharp) ─> measure-speed.py ─> out/samples.json │
          Remotion LaunchSub (PNG sub-frames) ─> accumulate.py ────┴─> mux.py (+ soundtrack) ─> check-sync.py
```

- **One timeline.** `src/timeline.ts` holds fps, size, the six acts, the bar/beat grid and every
  cue; `src/copy.ts` holds every line with its word timing. The acts, the cue exporter and the score
  all read them. `scripts/export-cues.ts` derives motion events with the picture's own functions:
  closed-form springs (`springHit`), velocity peaks of eased moves (`peakFrame`), the frame each
  applicant's seat fills, the frame each posting crosses the now edge.
- **Deterministic, sub-frame-safe animation.** Everything is a pure function of the (fractional)
  frame: `interpolate`/`Easing.bezier` tweens, an analytic damped-spring solution (exact between
  frames), seeded randomness, `@remotion/noise` for camera drift. No CSS transitions or animations.
- **Fonts.** `src/lib/FontGate.tsx` loads Inter (variable) and Figtree with `@remotion/fonts`,
  force-decodes every weight used and holds the render with `delayRender` until then, so no frame
  can capture a fallback face.
- **Typography.** Every headline's size is computed with `@remotion/layout-utils` (`fitText` with
  `validateFontIsLoaded`) inside the title-safe width, with authored line breaks (`src/lib/measure.ts`).
- **Backdrops.** The product's peach glows and the market's dark lift span only a few code values,
  so CSS gradients band. `scripts/make-backdrops.py` bakes them in float64 with TPDF dither.
- **Motion blur** (see below), **mux**, **sync check**, **contact sheets**.

### Motion blur

The final master is a film camera: each output frame is the average of *n* renders spread over a
216 deg shutter. `scripts/measure-speed.py` measures on-screen speed on the sharp render with dense
Farneback flow (large moving surfaces) and forward-backward-checked Lucas-Kanade corners (small fast
objects), and gives each frame enough samples that neighbouring samples are at most 3 px apart
(1 for still frames, 3-40 otherwise). `src/LaunchSub.tsx` renders those sub-frame times with
`<Freeze>`; `src/blur.ts` never lets a shutter cross a hard state change (the act seams and the
100+ downbeat, which would otherwise double-expose "99" and "100+"): the shutter is cut short
there and its samples stay evenly spaced. The sub-frames are written as
lossless PNGs straight from Chromium, and `scripts/accumulate.py` averages them in float32, dithers
(+-1 LSB TPDF) and quantizes once while converting to BT.709 4:2:0.

Remotion's `<HtmlInCanvasMotionBlur>` was tried on the reveal act (`Lab/BlurLab`, same shutter,
16 samples) and rejected on rendered evidence: its in-canvas averaging turned the product's peach
glows into hard concentric colour rings and shifted the neutral ground (`#F5F6F8` rendered as
`#F0F0F0`). The float path keeps both exact.

### Audio mastering and delivery

The mix is compressed, saturated and normalized to -14 LUFS integrated with a limiter whose
detector runs 4x oversampled (ceiling -2.2 dBTP, leaving room for the AAC encode). The picture is
rendered muted and the WAV (24-bit) is muxed by `scripts/mux.py` (AAC-LC 320 kb/s, faststart), so
encoder priming cannot shift it. `scripts/check-sync.py` cross-correlates the master WAV with the
decoded AAC around five transients (100+ hit, drop 1, a fresh-role birth, the #1 landing, the
lockup), fails above 1 ms, and measures true peak and loudness on the decoded delivery.

### Rendering (measured on an 8-core Apple M2, 8 GB)

- Preview (sharp, `--concurrency=6`): about 1.5 min. `render:chunks` (3 processes) about 1.3 min.
- Final: sharp render + optical flow (~4 min), about 7,100 sub-frames for 1,800 frames (about a third
  of the frames are still and render once; the fastest moves get up to 40 samples), accumulation and
  encode: about 23 min in total. The PNG sub-frames need ~20 GB of temporary disk.
- Headless Chromium is Remotion's own (Chrome for Testing 149); nothing machine-specific is configured.
- The ffmpeg Remotion ships is a reduced build (no raw-video pipes, no `select`), so the tools stay
  inside it: sub-frames are PNGs, the accumulator feeds 16-bit PNGs to its `image2pipe`, OpenCV
  decodes frames for analysis, and audio is decoded to 24-bit WAV for the checks.

## Run it

Needs Node 20+ and Python 3.11+. Remotion downloads its own headless Chromium, and provides the
ffmpeg/ffprobe the scripts use (`scripts/ff.py` prefers `$FFMPEG` or one on `PATH` if present).

```bash
npm install
npm run setup:python   # .venv with numpy scipy soundfile pyloudnorm opencv-python-headless pillow
npm run studio         # interactive preview (Launch, the acts one by one, Lab/BlurLab)
npm run cues           # timeline -> out/cues.json
npm run audio          # cues -> public/audio/soundtrack.wav (+ out/stems)
npm run render:preview # sharp picture + soundtrack -> out/applicable-launch-preview.mp4, sync check
npm run render         # motion-blurred master -> out/applicable-launch-final.mp4, sync check
npm run check          # sync + true peak + ffprobe delivery spec on the final
npm run sheet          # contact sheets from the final (out/contact-sheet.png, out/sheet-*.png)
npm run render:chunks  # optional parallel chunked preview render
```

## Layout

```
src/
  timeline.ts        fps, size, acts, bar/beat grid, every cue
  copy.ts            every on-screen line (approved copy only) and its word timing
  Launch.tsx         the film: six acts on exact frames (+ soundtrack in Studio)
  LaunchSub.tsx      the film as motion-blur sub-frames;  blur.ts  shutter + sample times
  acts/              Act1TooLate ... Act6Lockup, plus their data modules
  jobboard/          the fictional board, the hero posting, the market river
  product/ui.tsx     Applicable.ai pieces rebuilt from the app (tiles, rows, chips, factor bar)
  brand/             tokens, the mark and lockup (outlines extracted from the official SVG)
  fx/                camera, word reveals
  lib/               motion vocabulary + closed-form springs, font gate, text fitting
  lab/BlurLab.tsx    the in-browser motion-blur comparison
scripts/
  export-cues.ts  soundtrack.py  make-backdrops.py  measure-speed.py  accumulate.py
  mux.py  check-sync.py  validate.py  sheet.py  sheet.sh  render.sh  render-chunks.sh  ff.py
public/  fonts/ (Inter, Figtree - OFL)  brand/ (official SVGs)  fx/ (baked backdrops)  audio/
```

`out/` (renders, cues, samples, stems, sheets) is ignored: everything in it is reproducible.
