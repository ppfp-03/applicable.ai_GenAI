/*
 * Boot: preload, play the opening film once, then hand over to the deck.
 *
 * Public API (window.Applicable):
 *   replayTrailer()   play the film again from the start (also window.replayTrailer)
 *   skipTrailer()     jump to the final frame and hand over to the deck
 *   state             current state: LOADING | TRAILER_AUTOPLAY | PRESENTATION_READY
 *   player            {play, pause, seek(t), duration} — for tooling and debugging
 *
 * URL parameters (development):
 *   ?t=31.5    render that exact frame and hold (no autoplay) — used by tools/capture.mjs
 *   ?debug     show a timecode; Space pauses, , and . step ±1/30 s, [ and ] ±1 s, R replays
 *   ?skip      start directly in PRESENTATION_READY
 */
(function (A) {
  'use strict';

  const params = new URLSearchParams(location.search);
  const $ = (s) => document.querySelector(s);

  async function preload() {
    const faces = [
      '800 40px "Bricolage Grotesque"', '600 40px "Bricolage Grotesque"',
      '400 16px Figtree', '500 16px Figtree', '600 16px Figtree', '700 16px Figtree',
      '400 16px "JetBrains Mono"', '500 16px "JetBrains Mono"',
    ];
    const fonts = Promise.all(faces.map((f) => document.fonts.load(f))).then(() => document.fonts.ready);
    // Never hang the room on a font: continue after 4 s with whatever has loaded.
    await Promise.race([fonts, new Promise((r) => setTimeout(r, 4000))]);
  }

  async function boot() {
    const stage = $('#stage');
    A.fitStage(stage);
    const state = new A.PresentationState();
    const { tl } = A.buildTrailer($('#trailer'));

    const deck = new A.Deck({ cover: $('#trailer'), root: $('#deck'), hint: $('#hint'), counter: $('#counter') });

    const toReady = () => {
      if (!state.is(A.STATES.PRESENTATION_READY)) state.set(A.STATES.PRESENTATION_READY);
    };
    const clock = new A.Clock({ duration: tl.duration, onFrame: (t) => tl.render(t), onEnd: toReady });

    document.addEventListener('applicable:statechange', ({ detail }) => {
      if (detail.to === A.STATES.PRESENTATION_READY) deck.enable();
      if (detail.to === A.STATES.TRAILER_AUTOPLAY) deck.disable();
    });

    const api = {
      get state() {
        return state.value;
      },
      player: {
        play: () => clock.play(),
        pause: () => clock.pause(),
        seek: (t) => clock.seek(t),
        get t() {
          return clock.t;
        },
        duration: tl.duration,
      },
      replayTrailer() {
        clock.pause();
        deck.go(0, { instant: true });
        if (!state.is(A.STATES.TRAILER_AUTOPLAY)) state.set(A.STATES.TRAILER_AUTOPLAY);
        clock.seek(0);
        clock.play();
      },
      skipTrailer() {
        if (!state.is(A.STATES.TRAILER_AUTOPLAY)) return;
        clock.pause();
        clock.seek(tl.duration);
        toReady();
      },
    };
    Object.assign(A, api);
    Object.defineProperty(A, 'state', { get: () => state.value });
    window.replayTrailer = api.replayTrailer;

    // Escape skips the film (for rehearsals); nothing else interrupts it.
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.is(A.STATES.TRAILER_AUTOPLAY)) api.skipTrailer();
    });

    await preload();
    // Draw frame 0 and let the browser composite it before the clock starts.
    clock.seek(0);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    document.documentElement.classList.add('is-loaded');

    if (params.has('t')) {
      state.set(A.STATES.TRAILER_AUTOPLAY);
      clock.seek(parseFloat(params.get('t')) || 0);
    } else if (params.has('skip')) {
      clock.seek(tl.duration);
      state.set(A.STATES.PRESENTATION_READY);
    } else {
      state.set(A.STATES.TRAILER_AUTOPLAY);
      clock.play();
    }
    if (params.has('debug')) A.debugOverlay(clock, api);
    document.documentElement.dataset.ready = '1';
  }

  /** Timecode + scrubbing for rehearsal and review. */
  A.debugOverlay = function (clock, api) {
    const el = A.h('div.debug');
    document.body.append(el);
    const draw = () => {
      el.textContent = `${clock.t.toFixed(2)}s  ${clock.playing ? '▶' : '❚❚'}  ${A.state}`;
      requestAnimationFrame(draw);
    };
    draw();
    window.addEventListener('keydown', (e) => {
      if (!A.state || A.state === A.STATES.PRESENTATION_READY) return;
      const step = { ',': -1 / 30, '.': 1 / 30, '[': -1, ']': 1 }[e.key];
      if (e.key === ' ') clock.playing ? clock.pause() : clock.play();
      else if (step) {
        clock.pause();
        clock.seek(clock.t + step);
      } else if (e.key === 'r') api.replayTrailer();
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window.Applicable = window.Applicable || {});
