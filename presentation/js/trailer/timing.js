/*
 * The trailer's master cue sheet, in seconds. As in the reference film, picture and score read
 * the same numbers: every mark below sits on a 120 BPM grid (beat = 0.5 s, bar = 2 s), the
 * scenes schedule motion from them, and tools/export-cues.mjs hands them to the synthesizer.
 */
(function (A) {
  'use strict';

  const BPM = 120;
  const BEAT = 60 / BPM;
  const BAR = BEAT * 4;
  /** Time of bar n (1-indexed), plus beats. */
  const b = (bar, beat = 0) => (bar - 1) * BAR + beat * BEAT;

  A.T = {
    BPM, BEAT, BAR, b,

    // Phase 1 — the normal application problem (bars 1–5)
    open: b(1, 1), // 0.5
    verbs: b(3), // 4.0
    verbStep: 2 * BEAT, // a verb every two beats
    verb: (i) => b(3) + i * 2 * BEAT, // Find 4.0 … Repeat 10.0
    repeat: b(6), // 10.0

    // Phase 2 — information overload (bars 6–11)
    fieldFrom: b(6, 1), // 10.5
    fieldTo: b(10, 2), // 19.0
    overload: b(8, 2), // 15.0
    freeze: b(10, 3), // 19.5  hard stop
    harder: b(11), // 20.0

    // Phase 3 — the international student problem (bars 12–15)
    dusk: b(12), // 22.0
    abroad: b(12, 1), // 22.5
    constraints: b(13), // 24.0
    constraintStep: 2 * BEAT, // 24.0, 25.0, 26.0
    fieldTags: b(14, 1), // 26.5
    like: b(14, 3), // 27.5
    can: b(15, 1), // 28.5

    // Phase 4 — the central question (bars 16–17)
    question: b(16), // 30.0  near-silence
    markIn: b(17), // 32.0  the tile, a single bell
    light: b(17, 2), // 33.0  resolution: D minor → D major
    dock: b(18, 1), // 34.5

    // Phase 5 — Applicable.ai organises the chaos (bars 17–22)
    organise: b(17, 3), // 33.5
    panels: b(18, 2), // 35.0
    flipCv: b(19), // 36.0  the CV turns over into facts
    flipJd: b(19, 2), // 37.0  the job post turns over into requirements
    understand: b(20), // 38.0
    links: b(21), // 40.0
    linkStep: BEAT,
    verdictSplit: b(22), // 42.0

    // Phase 6 — from information to decision (bars 23–26)
    list: b(23), // 44.0
    statuses: b(23, 3), // 45.5
    statusStep: BEAT,
    demote: b(24, 2), // 47.0
    verify: b(25), // 48.0
    ask: b(25), // 48.0
    answer: b(25, 2), // 49.0
    recompute: b(26), // 50.0
    prioritise: b(26, 1), // 50.5

    // Phase 7 — resolution (bars 27–30)
    focus: b(27), // 52.0
    card: b(27, 1), // 52.5
    product: b(28, 2), // 55.0  the real product arrives behind the card
    toMark: b(29, 1), // 56.5
    tagline: b(29, 3), // 57.5
    handoff: b(30, 2), // 59.0
    end: b(31), // 60.0
  };
})(window.Applicable = window.Applicable || {});
