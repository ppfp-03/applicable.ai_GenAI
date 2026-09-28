# Applicable.ai — opening film and presentation shell

A 59-second, silent opening film that runs as the first moment of a single-page HTML
presentation. When the film ends, its final frame becomes the cover slide, and the page hands
control to the deck. The page never navigates, reloads or opens a window.

Open `index.html` in Chrome, either directly (`file://` works) or through any static server.
It has no dependencies and makes no network requests. Fonts are embedded and the logo is
inlined.

## The story

One continuous space, seen through one virtual camera. Objects are introduced once and then
transformed. There are no cuts between slides.

| Time | Phase | What happens |
| --- | --- | --- |
| 0–12 s | The normal problem | "Entering the job market is already a job." Seven verbs (*Find. Read. Compare. Adapt. Write. Apply. Repeat.*) each put their own object on the desk. "Repeat." pulls the camera back. |
| 12–22 s | Overload | Roles, deadlines, statuses, reminders and files keep arriving, faster and faster, and live counters tally them. Everything freezes: *And then it gets harder.* |
| 22–30 s | Abroad | Dusk. The camera finds one attractive role ("Looks like a great fit") and three constraints attach to it: **work authorization, language, visa / sponsorship**. Pulling back, every role carries constraints. *Do I like this job? → Can I actually apply?* |
| 30–34 s | The question | Defocus, then *Which opportunity is actually worth your time?* The Applicable.ai tile appears, and daylight spreads out of it. |
| 34–44 s | Organise | As the light reaches each object, it straightens and goes to its place: roles into one pile, the CV and the job post into two panels. Each document is read and collapses into **sourced facts** (`CV`, `YOU`, `JOB`, `RULE`). The UK right to work is *Not stated in your CV*. Matching shows **strong fit (92) ≠ eligibility (explicit conflict)**. *Understand.* |
| 44–52 s | Decide | Four roles, sorted by fit alone. Eligibility resolves: the best fit is an *Explicit conflict* and moves under *Not for now* (visible, never hidden). One role *Needs verification*, so the product asks *Are you authorised to work in the UK?* instead of guessing. The answer is Yes, the list recomputes, and that role becomes #1. *Verify. Prioritise.* |
| 52–59 s | Resolution | One calm card: *Apply this week*, eligibility, fit, deadline, and the reason with highlighted evidence. It folds into the tile, and the lockup appears with *Know which opportunity deserves your time.* |

The film uses the Applicable.ai design system: warm paper, mandarin for action, highlighter
yellow for evidence, sky blue for the AI's voice, and go / clarify / skip for verdicts. There
is no red: *not for now* is slate, not an error. The companies are the fictional demo set,
shown as monograms. All UI is reconstructed from tokens; none of it is a screenshot.

## States and hand-off

```
LOADING ──fonts ready──▶ TRAILER_AUTOPLAY ──film ends / Esc──▶ PRESENTATION_READY
                                ▲                                     │
                                └────────── replayTrailer() ──────────┘
```

- The film plays automatically once, on load. Deck input is ignored while it plays; **Esc**
  skips to the end.
- In `PRESENTATION_READY`, the deck takes input: arrows, PageUp/PageDown, Space and Enter,
  clicks (the left fifth of the screen goes back), horizontal trackpad swipes and touch
  swipes. A quiet "→ to continue" hint appears.
- Going back to slide 0 shows the cover (the final frame). It never restarts the film. Only an
  explicit `replayTrailer()` does.
- Every transition emits `applicable:statechange` on `document` with `{from, to}`. Slide changes
  emit `applicable:slidechange` with `{index}`.

```js
document.addEventListener('applicable:statechange', (e) => console.log(e.detail));
Applicable.state;            // 'TRAILER_AUTOPLAY' | 'PRESENTATION_READY' | 'LOADING'
Applicable.replayTrailer();  // also window.replayTrailer()
Applicable.skipTrailer();
Applicable.player.seek(31.5);
```

The deck in `index.html` has three placeholder slides that prove the hand-off. To build the
real deck, replace the `<section class="slide">` elements inside `#deck`.

## How it works

The film is **deterministic**: every visual property is a pure function of the playhead time.
Scenes don't run anything while playing. At start-up they schedule keyframes on persistent
actors, and each display frame then evaluates `render(t)`. This gives the following:

- smooth, stable timing (no per-frame integration, so there is no drift);
- exact seek, scrub, replay and pause;
- frame-perfect capture for review (`tools/capture.mjs`);
- pausing when the tab is hidden, so the film never "plays unseen".

Only transforms, opacity, clip and (briefly) blur are animated. The whole world moves under
one camera transform.

```
index.html                 page shell: stage, trailer layer, deck, hint
css/fonts.css              embedded woff2 (works from file://), generated by tools/build-assets.py
css/tokens.css             design-system tokens (copied from design-system/, fonts removed)
css/stage.css              1920×1080 stage, letterboxed and scaled to any window
css/trailer.css            reconstructed product UI for the film
css/deck.css               placeholder slides and the presenter hint
assets/brand.js            mark and wordmark SVG, inlined (generated from static/*.svg)
js/core/easing.js          easing curves
js/core/timeline.js        Track / Actor / Timeline: the deterministic engine
js/core/clock.js           playback clock (rAF, pause, seek, hidden-tab pause)
js/core/stage.js           stage fit, DOM helper, seeded PRNG
js/trailer/content.js      all copy and data. Edit words here.
js/trailer/timing.js       the master cue sheet. Retime the film here.
js/trailer/components.js   DOM factories: cards, documents, rows, question, final card
js/trailer/scenes/0*.js    choreography, one file per phase
js/trailer/trailer.js      layers, camera, background, scene assembly
js/presentation/state.js   the TRAILER_AUTOPLAY → PRESENTATION_READY state machine
js/presentation/deck.js    minimal deck and input handling
js/main.js                 boot, preload, public API, debug overlay
tools/capture.mjs          render stills or every frame with Playwright
tools/build-assets.py      regenerate fonts.css, tokens.css and brand.js from design-system/ and static/
```

## Development

- `index.html?debug` shows a timecode. **Space** pauses, `,` and `.` step one frame, `[` and `]`
  step one second, **R** replays.
- `index.html?t=42.5` renders that exact frame and holds it.
- `index.html?skip` starts directly in `PRESENTATION_READY`.

Review frames or a full MP4:

```bash
npm i -D playwright-core          # once, anywhere on the path
node tools/capture.mjs stills out/ 5 22.5 41 48.8
node tools/capture.mjs video out/frames --fps 30 --scale 1
ffmpeg -framerate 30 -i out/frames/%05d.png -pix_fmt yuv420p -crf 18 out/trailer.mp4
```

Set `CHROMIUM_PATH` if Playwright can't find a browser.

## Notes

- The film is 59.4 s long (`T.end` in `timing.js`). Pacing is designed for silence, with no
  audio anywhere.
- Target: 1920×1080 at 60 fps in desktop Chrome with GPU compositing. The densest moments
  (about 90 objects in phase 2–3, and the defocused frame at 30–34 s) are the heaviest. In
  headless Chrome *without* a GPU, the film holds 60 fps everywhere except 25–35 s, where it
  drops to roughly 15–30 fps, and the full-frame blur is the main cost. Rehearse on the
  presentation laptop. If the defocus stutters there, lower `blur` in
  `scenes/04-question.js` (0 disables it).
- `prefers-reduced-motion` is deliberately not applied: this is a film the presenter chose to
  play. Press **Esc** to skip it.
