# Applicable.ai — opening film and presentation shell

A 60-second opening film with an original synthesized score. It runs as the first moment of a
single-page HTML presentation. When the film ends, its last frame becomes the cover slide and
the page hands control to the deck. The page never navigates, reloads or opens a window.

Open `index.html` in Chrome, either directly (`file://` works) or through any static server.
It makes no network requests: the font, logo, product screenshot and music are all local.

## The story

The film is one continuous 3D space, seen through one camera. It is built in the app's own
visual language (Inter, glass cards on the app's glow background, dark monograms, priority
numbers, green/amber/red chips) and ends inside the real product.

**Chaos is tilted, order is frontal.** The problem is shown on a desk seen from an angle, then
from above. Once Applicable.ai arrives, everything straightens and faces the viewer.

| Time | Phase | Picture | Score |
| --- | --- | --- | --- |
| 0–10 s | The normal problem | "Entering the job market is already a job." The camera tilts down onto a desk. Seven verbs turn over on a drum (*Find. Read. Compare. Adapt. Write. Apply. Repeat.*), and each drops its object onto the table. On "Repeat." the drum spins through the whole loop. | D minor. A clock that ticks, and a task motif on every verb. |
| 10–22 s | Overload | Seen from above while the camera orbits, the desk keeps receiving roles, deadlines, statuses, to-dos and files, faster and faster. Counters tally the load. On the beat everything stops dead: *And then it gets harder.* | The ostinato tightens and a riser builds. Dead silence, then one low hit. |
| 22–30 s | Abroad | Dusk on the stage. The camera swoops down and lifts one attractive role toward the lens ("Looks like a great fit"). **Work authorization, language, visa / sponsorship** unfold beneath it like an accordion. Pulling back up, every role carries constraints. *Do I like this job? → Can I actually apply?* | A dissonant drone and a slow heartbeat. Each constraint lands low. |
| 30–34 s | The question | The desk sinks away into depth and softness. *Which opportunity is actually worth your time?* The Applicable.ai tile turns toward us, and a warm bloom returns the stage to the app's colours. | Near-silence and one thin note. A bell for the tile, then the same key opens into **D major**. |
| 34–44 s | Organise | As the light reaches each object it lifts, straightens and flies to its place: roles into one stack, the CV and the job post into two panels. Each document is read, then **turns over**, and its back is structured, sourced data (`CV`, `YOU`, `JOB`, `RULE`; the UK is *Not stated in your CV*). Matching shows **strong fit (92) ≠ eligibility (explicit conflict)**. *Understand.* | A warm pad and a felt-piano arpeggio. Each row is a note of the scale. |
| 44–52 s | Decide | Four roles lift off the stack, sorted by fit. Eligibility resolves row by row. The best fit is an *Explicit conflict* and sinks back into *Not for now* (visible, never hidden). One role *Needs verification*, so the product asks *Are you authorised to work in the UK?* The answer is Yes, and the list recomputes: that role rises toward the viewer and over the others to #1. *Verify. Prioritise.* | Consonant interface sounds. A low muted dyad for the conflict, a rising arpeggio for the recompute. |
| 52–60 s | Resolution | The #1 row flips into the app's own **Next best action** card. Then the **real Home screen** (captured from the running app) arrives out of depth and the card lands in its slot. The story folds into the lockup and the app's promise: *Know where to apply this week, and why.* | A final D(add9) rings out over the lockup. |

## Sound and the start screen

The score and every sound effect are synthesized from code (`tools/soundtrack.py`), on the
exact moments the picture uses. The cues are exported from the same timeline, as in the
reference film [Leonxlnx/claude-launchvideo](https://github.com/Leonxlnx/claude-launchvideo),
whose DSP helpers are adapted here under MIT (see `tools/THIRD_PARTY_NOTICES.md`).

- In the browser, the **audio is the master clock**. The picture reads its time from what the
  listener is hearing, output latency included, so sound and picture stay in sync on any
  machine.
- Browsers only allow sound after a user gesture. Unless the page is already allowed to play
  audio, a quiet start screen waits for **one click or key** from the presenter. Kiosk setups
  can instead launch Chrome with `--autoplay-policy=no-user-gesture-required`.
- `index.html?muted` plays the film silently, with no start screen.
- Mastered to −16 LUFS, a level suited to a presentation room.

## States and hand-off

```
LOADING ──(start screen)──▶ TRAILER_AUTOPLAY ──film ends / Esc──▶ PRESENTATION_READY
                                   ▲                                      │
                                   └────────── replayTrailer() ───────────┘
```

- The film plays once, on load. Deck input is ignored while it plays; **Esc** skips to the end.
- In `PRESENTATION_READY`, the deck takes input: arrows, PageUp/PageDown, Space and Enter,
  clicks (the left fifth of the screen goes back), horizontal trackpad swipes and touch
  swipes. A quiet "→ to continue" hint appears.
- Going back to slide 0 shows the cover. It never restarts the film. Only an explicit
  `replayTrailer()` does.
- Transitions emit `applicable:statechange` (`{from, to}`) and `applicable:slidechange`
  (`{index}`) on `document`.

```js
Applicable.state;            // 'LOADING' | 'TRAILER_AUTOPLAY' | 'PRESENTATION_READY'
Applicable.replayTrailer();  // also window.replayTrailer()
Applicable.skipTrailer();
Applicable.player.seek(31.5);
```

The deck in `index.html` has three placeholder slides that prove the hand-off. To build the
real deck, replace the `<section class="slide">` elements inside `#deck`.

## How it works

- **Deterministic.** Every visual property is a pure function of the playhead time. Scenes
  schedule keyframes and sound cues once, at start-up. Seek, replay and frame-exact capture
  all give the same picture.
- **3D with CSS.** Actors have `x, y, z, rotateX, rotateY, rotate, scale`. The world sits in a
  perspective box and one camera (position, zoom, tilt, orbit, dolly) moves it. There is no
  WebGL and no library.
- **Musical grid.** `timing.js` places every mark on 120 BPM (a beat every 0.5 s, a bar every
  2 s). The scenes read those marks, and the score is built from the same marks.
- **The app's stage.** The four glows come from `ui/shell.py`, with colours from
  `ui/palette.py`. They drift, and their colour follows the story: cool while it's a problem,
  dusk abroad, warm once solved.

```
index.html                 page shell: stage, trailer, start screen, deck, hint
css/fonts.css              Inter, embedded (generated)
css/stage.css              1920×1080 stage, scaled to any window
css/trailer.css            the app's visual language for the film
css/deck.css               placeholder slides, hint, start screen
assets/app-home.jpg        the real Home screen, captured from the running app (demo data)
assets/brand.js            mark and wordmark SVG (generated from static/*.svg)
assets/soundtrack.js       the score, MP3 as base64 (generated)
audio/cues.json            every sync point, exported from the film (generated)
js/core/                   easing, deterministic timeline (3D actors), audio-mastered clock, stage
js/trailer/content.js      all copy and data. Edit words here.
js/trailer/timing.js       the cue sheet on the musical grid. Retime here.
js/trailer/components.js   app-style cards, rows, question, Next best action, product
js/trailer/scenes/0*.js    choreography and sound cues, one file per phase
js/trailer/trailer.js      layers, 3D camera, glow moods, cue registry
js/presentation/           state machine and the minimal deck
js/main.js                 boot, start screen, public API, debug overlay
tools/                     asset, cue, music, capture and render scripts
```

## Rebuilding

All tools need Node with `playwright-core` (`npm i -D playwright-core`) and a Chromium
(`CHROMIUM_PATH`). Python needs `numpy scipy soundfile pyloudnorm Pillow` (see
`video/requirements-audio.txt`), plus `ffmpeg`.

```bash
python3 tools/build-assets.py        # Inter + logo, from static/ and ui/css/base.css
node tools/export-cues.mjs           # audio/cues.json from the film's timeline
python3 tools/soundtrack.py          # audio/soundtrack.wav
node tools/embed-audio.mjs           # assets/soundtrack.js (+ measured decoder offset)
tools/render-preview.sh out/film.mp4 --sub 4   # the whole chain, MP4 with motion blur + sound
```

After changing timings or cues, re-run the three audio steps so the score follows the picture.

For review:
- `index.html?debug` shows a timecode: **Space** pauses, `,` and `.` step one frame, `[` and `]`
  step one second, **R** replays.
- `index.html?t=42.5` renders that exact frame and holds it.
- `index.html?skip` starts directly in `PRESENTATION_READY`.

## Notes

- Target: 1920×1080 at 60 fps in desktop Chrome with GPU compositing. The densest moments
  (about 80 objects in 3D during phases 2–3, and the defocus at 30–34 s) are the heaviest.
  Rehearse on the presentation laptop. If the defocus stutters there, lower `blur` in
  `scenes/04-question.js` (0 disables it).
- `prefers-reduced-motion` is deliberately not applied: this is a film the presenter chose to
  play. Press **Esc** to skip it.
