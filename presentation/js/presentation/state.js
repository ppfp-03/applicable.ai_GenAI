/*
 * Presentation state machine — the boundary between the film and the deck.
 *
 *   LOADING ──fonts ready──▶ TRAILER_AUTOPLAY ──film ends / skip──▶ PRESENTATION_READY
 *                                   ▲                                     │
 *                                   └──────────── replayTrailer() ────────┘
 *
 * Every transition is announced as a DOM event on `document`:
 *   document.addEventListener('applicable:statechange', (e) => e.detail) // {from, to}
 * The deck listens for PRESENTATION_READY; nothing in the deck can move the state back to
 * TRAILER_AUTOPLAY except an explicit replayTrailer() call.
 */
(function (A) {
  'use strict';

  const STATES = Object.freeze({
    LOADING: 'LOADING',
    TRAILER_AUTOPLAY: 'TRAILER_AUTOPLAY',
    PRESENTATION_READY: 'PRESENTATION_READY',
  });

  const ALLOWED = {
    LOADING: ['TRAILER_AUTOPLAY', 'PRESENTATION_READY'],
    TRAILER_AUTOPLAY: ['PRESENTATION_READY'],
    PRESENTATION_READY: ['TRAILER_AUTOPLAY'],
  };

  class PresentationState {
    constructor() {
      this.value = STATES.LOADING;
    }
    is(s) {
      return this.value === s;
    }
    set(to) {
      const from = this.value;
      if (from === to) return;
      if (!ALLOWED[from].includes(to)) throw new Error(`Illegal transition ${from} → ${to}`);
      this.value = to;
      document.documentElement.dataset.state = to;
      document.dispatchEvent(new CustomEvent('applicable:statechange', { detail: { from, to } }));
    }
  }

  A.STATES = STATES;
  A.PresentationState = PresentationState;
})(window.Applicable = window.Applicable || {});
