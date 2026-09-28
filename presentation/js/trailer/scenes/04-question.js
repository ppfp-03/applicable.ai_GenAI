/*
 * Phase 4 — The central question (≈30–34 s).
 * The desk goes out of focus and quiet. One question. Then a small mandarin tile appears
 * where the question was, and daylight spreads out of it: Applicable.ai does not cut in,
 * it starts re-lighting — and re-ordering — the world that is already there.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function question(ctx) {
    const { T, content: K, C, h, hud, light, place, inner, cam, shared } = ctx;

    // Defocus and quiet.
    cam.to(T.question - 0.1, 1.0, { blur: 7, o: 0.4 }, 'inOutSine');

    const q = C.headline(K.question, 'center xl on-dark');
    const qA = place(q, hud, { x: 960, y: 530 });
    [...q.querySelectorAll('.hl-line')].forEach((ln, i) =>
      inner(ln, { y: 140 }).to(T.question + 0.3 + i * 0.4, 1.0, { y: 0 }, 'outExpo')
    );
    qA.to(T.markIn - 0.1, 0.6, { o: 0, y: 470, s: 0.97 }, 'inOutCubic');

    // The lockup group: mark centred first, wordmark tucked behind it.
    const MARK = 96, GAP = 44;
    const WM_H = Math.round(MARK * 0.7);
    const WM_W = Math.round(WM_H * A.brand.wordmarkAspect);
    const W = MARK + GAP + WM_W;
    const group = h('div.lockup', { style: { width: W + 'px', height: MARK + 'px' } });
    const mark = C.mark(MARK);
    const word = C.wordmark(WM_H);
    group.append(word, mark);
    const groupA = place(group, hud, { x: 960, y: 540 }, null, 'lockup');
    const markA = inner(mark, { x: (W - MARK) / 2, s: 0, r: -12 }, null, 'lockupMark');
    const wordA = inner(word, { x: MARK + GAP - 24, o: 0 }, { anchor: 'none', clip: true }, 'lockupWord');
    wordA.track('cr').keys[0].v = 100;
    mark.style.position = word.style.position = 'absolute';
    mark.style.left = '0px';
    mark.style.top = '0px';
    word.style.left = '0px';
    word.style.top = Math.round((MARK - WM_H) / 2) + 'px';
    shared.lockup = { groupA, markA, wordA, W, MARK, GAP };

    markA.to(T.markIn, 0.7, { s: 1, r: 0 }, 'outBack');

    // Daylight: a paper disc grows from the tile until it fills the frame.
    const disc = h('div.daylight');
    const discA = place(disc, light, { x: 960, y: 540, s: 0 });
    discA.to(T.light, 1.9, { s: 1 }, 'outCubic');
    cam.to(T.light + 0.15, 1.1, { blur: 0, o: 1 }, 'outCubic');

    // Lockup opens: mark slides left, wordmark slides out from behind it.
    markA.to(T.light + 0.4, 0.75, { x: 0 }, 'inOutCubic');
    wordA.to(T.light + 0.75, 0.7, { x: MARK + GAP, o: 1, cr: 0 }, 'outCubic');

    // Dock top-left, where it stays as the product's quiet presence.
    groupA.to(T.dock, 0.9, { x: 64 + (W * 0.36) / 2, y: 64, s: 0.36 }, 'inOutCubic');
  });
})(window.Applicable = window.Applicable || {});
