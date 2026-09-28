/*
 * The trailer's master clock, in seconds. Scenes schedule relative to these marks, so the
 * pacing of the whole film can be tuned here without touching choreography.
 */
(function (A) {
  'use strict';

  const verbs0 = 4.0;
  const verbStep = 1.05;

  A.T = {
    // Phase 1 — the normal application problem
    open: 0.5,
    verbs: verbs0,
    verbStep,
    verb: (i) => verbs0 + i * verbStep, // Find … Repeat
    repeat: verbs0 + 6 * verbStep, // 10.3

    // Phase 2 — information overload
    fieldFrom: 10.4,
    fieldTo: 19.2,
    overload: 15.6,
    freeze: 19.4,
    harder: 19.9,

    // Phase 3 — the international student problem
    dusk: 22.0,
    abroad: 22.3,
    constraints: 24.1,
    constraintStep: 0.75,
    fieldTags: 26.6,
    like: 27.2,
    can: 28.2,

    // Phase 4 — the central question
    question: 30.1,
    markIn: 32.4,
    light: 33.0,
    dock: 34.65,

    // Phase 5 — Applicable.ai organises the chaos
    organise: 33.3,
    panels: 34.8,
    scanCv: 36.2,
    facts: 37.1,
    scanJd: 37.0,
    reqs: 38.0,
    understand: 38.6,
    links: 40.0,
    verdictSplit: 42.0,

    // Phase 6 — from information to decision
    list: 44.0,
    statuses: 45.7,
    demote: 46.9,
    verify: 47.9,
    ask: 48.0,
    answer: 49.0,
    recompute: 49.8,
    prioritise: 50.4,

    // Phase 7 — resolution
    focus: 52.0,
    card: 52.3,
    toMark: 55.6,
    lockup: 56.4,
    tagline: 57.0,
    handoff: 58.4,
    end: 59.4,
  };
})(window.Applicable = window.Applicable || {});
