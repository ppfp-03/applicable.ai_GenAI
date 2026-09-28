/*
 * Phase 4 — The central question (bars 16–17, 30–34 s).
 * The desk sinks away into depth and softness; near-silence. One question. Then the
 * Applicable.ai tile turns towards us, and a warm bloom spreads out of it: the stage returns
 * to the app's own colours, and the lockup settles top-left, where the app keeps it.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function question(ctx) {
    const { T, content: K, C, h, hud, bloomLayer, place, inner, cam, shared, sfx, mood, glows, GLOWS } = ctx;

    // The chaos recedes: pushed back in depth, defocused, glows drawn in and dimmed.
    cam.to(T.question - 0.2, 1.4, { z: -520, blur: 6, o: 0.45 }, 'inOutCubic');
    mood.to(T.question - 0.2, 1.4, { vig: 1 }, 'inOutSine');
    glows.forEach((g, i) => g.to(T.question - 0.2, 2.2, { x: 960 + (GLOWS[i][0] - 960) * 0.45, y: 540 + (GLOWS[i][1] - 540) * 0.45, s: 0.7 }, 'inOutSine'));
    sfx(T.question - 0.2, 'recede');

    const q = C.headline(K.question, 'center xl');
    q.querySelectorAll('.hl-line')[1].innerHTML = 'actually <span style="color:var(--accent)">worth your time?</span>';
    const qA = place(q, hud, { x: 960, y: 530 });
    [...q.querySelectorAll('.hl-line')].forEach((ln, i) => inner(ln, { y: 140 }).to(T.question + 0.3 + i * 0.45, 1.0, { y: 0 }, 'outExpo'));
    qA.to(T.markIn - 0.2, 0.6, { o: 0, s: 0.94 }, 'inOutCubic');

    // The lockup group: the tile first, the wordmark after.
    const MARK = 104, GAP = 46;
    const WM_H = Math.round(MARK * 0.7);
    const WM_W = Math.round(WM_H * A.brand.wordmarkAspect);
    const W = MARK + GAP + WM_W;
    const group = h('div.lockup.d3', { style: { width: W + 'px', height: MARK + 'px', perspective: '900px' } });
    const mark = C.mark(MARK);
    const word = C.wordmark(WM_H);
    group.append(word, mark);
    const groupA = place(group, hud, { x: 960, y: 540 }, null, 'lockup');
    const markA = inner(mark, { x: (W - MARK) / 2, ry: -90, s: 0.6, o: 0 }, null, 'lockupMark');
    const wordA = inner(word, { x: MARK + GAP - 24, o: 0 }, { anchor: 'none', clip: true }, 'lockupWord');
    wordA.track('cr').keys[0].v = 100;
    mark.style.position = word.style.position = 'absolute';
    mark.style.left = mark.style.top = '0px';
    word.style.left = '0px';
    word.style.top = Math.round((MARK - WM_H) / 2) + 'px';
    shared.lockup = { groupA, markA, wordA, W, MARK, GAP };

    markA.to(T.markIn, 0.2, { o: 1 }).to(T.markIn, 0.9, { ry: 0, s: 1 }, 'outBack');
    sfx(T.markIn, 'bell');

    // Bloom: warm light out of the tile; the app's stage comes back.
    const bloom = place(h('div.bloom'), bloomLayer, { x: 960, y: 540, s: 0, o: 1 });
    bloom.to(T.light - 0.05, 1.8, { s: 1 }, 'outCubic').to(T.light + 1.8, 2.5, { o: 0 }, 'inOutSine');
    mood.to(T.light, 1.2, { tense: 0, night: 0, vig: 0, bloom: 1 }, 'outCubic');
    mood.to(T.light + 3, 4, { bloom: 0.35 }, 'inOutSine');
    glows.forEach((g, i) => g.to(T.light, 2.4, { x: GLOWS[i][0], y: GLOWS[i][1], s: 1.12 }, 'outCubic'));
    cam.to(T.light + 0.1, 1.3, { blur: 0, o: 1, z: 0 }, 'outCubic');
    sfx(T.light, 'resolve');

    markA.to(T.light + 0.3, 0.75, { x: 0 }, 'inOutCubic');
    wordA.to(T.light + 0.65, 0.7, { x: MARK + GAP, o: 1, cr: 0 }, 'outCubic');
    sfx(T.light + 0.65, 'word', { i: 6 });

    // Dock top-left, as in the app's header.
    const DS = 0.34;
    groupA.to(T.dock, 0.9, { x: 56 + (W * DS) / 2, y: 58, s: DS }, 'inOutCubic');
  });
})(window.Applicable = window.Applicable || {});
