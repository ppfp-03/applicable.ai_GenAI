/*
 * Phase 7 — Final resolution (bars 27–30, 52–60 s).
 * Everything else steps back. The #1 row flips over into the app's own "Next best action"
 * card: verdict, deadline, the checks, the reason. Then the real product arrives out of
 * depth — the Home screen as it runs — and the card lands in its slot: this is where it
 * lives. The story folds into the lockup and the app's own promise.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function resolve(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared, sfx, mood } = ctx;
    const R = shared.rows;

    // Clear the stage around #1.
    [R.N, R.U, R.D, R.divA].forEach((a, i) => a.to(T.focus - 0.3 + i * 0.05, 0.5, { z: -160, o: 0 }, 'inCubic'));
    R.titleA.to(T.focus - 0.3, 0.4, { o: 0 });
    shared.trio.trioA.to(T.focus, 0.5, { o: 0 });

    // #1 comes to the centre and flips over (on X) into the full card.
    R.B.to(T.focus, 0.5, { y: 540, z: 60 }, 'inOutCubic');
    R.B.to(T.card, 0.4, { rx: 90 }, 'inCubic').set(T.card + 0.4, { o: 0 });
    // Product and card share one group: once the card has landed they leave as a single
    // layer, so the app's own card underneath can never show through a half-faded one.
    const group = h('div.d3');
    const groupA = place(group, world, { x: 0, y: 0 }, { anchor: 'none' }, 'productGroup');
    const card = C.nextBest(K.nextBest);
    card.classList.add('in-slot');
    const cardA = place(card, group, { x: 960, y: 540, z: 60, rx: -90, s: 1.18, o: 0 }, null, 'nextBest');
    cardA.set(T.card + 0.4, { o: 1 }).to(T.card + 0.4, 0.8, { rx: 0 }, 'outBack');
    sfx(T.card, 'flip');
    sfx(T.card + 0.5, 'card');
    const checks = [...card.querySelectorAll('.nba-checks > div')];
    checks.forEach((el, i) => {
      inner(el, { o: 0, x: -14 }).to(T.card + 1.0 + i * 0.22, 0.4, { o: 1, x: 0 }, 'outCubic');
      sfx(T.card + 1.0 + i * 0.22, 'met', { i: 11 + i });
    });

    // The real product arrives from depth; the card lands in its "next best action" slot.
    // Screenshot geometry (1600×1000 app stage): that card spans x 490–1110, y 160–478.
    const PS = 0.9;
    const product = C.product('assets/app-home.jpg');
    const productA = place(product, group, { x: 960, y: 560, z: -1400, rx: 24, o: 0 }, null, 'product');
    group.insertBefore(product, card); // behind the card
    productA.to(T.product, 0.3, { o: 1 }).to(T.product, 1.4, { z: 0, rx: 0, y: 540, s: PS }, 'outCubic');
    const slotW = 620 * PS, slotY = 540 + (319 - 500) * PS;
    cardA.to(T.product + 0.35, 1.1, { y: slotY, z: 2, s: slotW / 780 }, 'inOutCubic');
    cam.to(T.product, 1.4, { rx: 9, ry: -7, s: 0.96 }, 'inOutCubic');
    sfx(T.product, 'whoosh', { d: 1.4, gain: 0.7 });
    sfx(T.product + 1.35, 'land', { gain: 1 });
    mood.to(T.product, 1.5, { bloom: 0.8 }, 'inOutSine');

    // Fold into the lockup.
    cam.to(T.toMark, 1.0, { rx: 0, ry: 0, s: 1 }, 'inOutCubic');
    groupA.to(T.toMark, 0.8, { z: -900, o: 0 }, 'inCubic');
    const L = shared.lockup;
    const S = 1.15, LY = 470;
    L.groupA.to(T.toMark + 0.5, 0.85, { x: 960, y: LY, s: S }, 'inOutCubic');
    sfx(T.toMark + 0.5, 'whoosh', { d: 1.0, gain: 0.5 });

    const tag = C.headline(K.tagline, 'center lg');
    tag.querySelectorAll('.hl-line')[1].innerHTML = 'this week, <span class="soft">and why.</span>';
    const tagA = place(tag, hud, { x: 960, y: 640 }, null, 'tagline');
    [...tag.querySelectorAll('.hl-line')].forEach((ln, i) => {
      inner(ln, { y: 100 }).to(T.tagline + i * 0.3, 0.9, { y: 0 }, 'outExpo');
    });
    sfx(T.tagline, 'final');

    // Settle into the presentation's cover.
    L.groupA.to(T.handoff, 0.9, { y: LY - 20 }, 'inOutCubic');
    tagA.to(T.handoff, 0.9, { y: 620 }, 'inOutCubic');
  });
})(window.Applicable = window.Applicable || {});
