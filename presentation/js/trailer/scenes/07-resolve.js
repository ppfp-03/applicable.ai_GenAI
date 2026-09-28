/*
 * Phase 7 — Final resolution (≈52–59 s).
 * Everything else leaves. The #1 row opens into one calm, complete decision: verdict,
 * eligibility, fit, deadline, and the reason with its evidence. Then the whole story folds
 * into the mark, and the lockup lands where the presentation begins.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function resolve(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared } = ctx;
    const R = shared.rows;

    // Clear the stage around #1.
    [R.N, R.U, R.D, R.divA].forEach((a, i) => a.to(T.focus - 0.25 + i * 0.05, 0.45, { y: a.v('y') + 40, o: 0 }, 'inCubic'));
    R.titleA.to(T.focus, 0.4, { o: 0 });
    shared.trio.trioA.to(T.focus, 0.5, { o: 0 });

    // #1 row lifts to centre and hands over to the full card.
    R.B.to(T.focus + 0.05, 0.6, { y: 560 }, 'inOutCubic').to(T.card + 0.15, 0.3, { o: 0 });
    const card = C.finalCard(K.finalCard);
    const cardA = place(card, world, { x: 960, y: 560, o: 0, ct: 40, cb: 40 }, { clip: true, radius: 20 }, 'finalCard');
    cardA.to(T.card, 0.25, { o: 1 }).to(T.card, 0.85, { ct: 0, cb: 0 }, 'outCubic');
    const parts = [...card.querySelectorAll('.final-top, .final-title, .final-where, .tile, .why')];
    parts.forEach((p, i) => inner(p, { o: 0, y: 14 }).to(T.card + 0.35 + i * 0.07, 0.55, { o: 1, y: 0 }, 'outCubic'));

    // The evidence highlight is drawn like a marker stroke.
    const hl = card.querySelector('.hl');
    const t0 = T.card + 1.1;
    let last = -1;
    ctx.tl.hook((t) => {
      const p = Math.round(A.prog(t, t0, t0 + 0.7, 'inOutSine') * 1000) / 10;
      if (p !== last) hl.style.backgroundSize = `${(last = p)}% 100%`;
    });

    cam.to(T.card, T.toMark - T.card, { s: 1.16 }, 'inOutSine');
    cam.to(T.toMark, 0.7, { s: 1, y: 540 }, 'inOutCubic');

    // Fold into the mark.
    const L = shared.lockup;
    const S = 1.1;
    const LY = 505;
    const markX = 960 - (L.W * S) / 2 + (L.MARK * S) / 2;
    cardA.to(T.toMark, 0.8, { x: markX, y: LY, s: 0.1, o: 0 }, 'inOutCubic');
    L.groupA.to(T.toMark + 0.05, 0.95, { x: 960, y: LY, s: S }, 'inOutCubic');

    const tag = C.headline([K.tagline], 'center tagline');
    const tagA = place(tag, hud, { x: 960, y: 632 }, null, 'tagline');
    inner(tag.querySelector('.hl-line'), { y: 70 }).to(T.tagline, 0.9, { y: 0 }, 'outExpo');

    // Settle into the presentation's cover composition.
    L.groupA.to(T.handoff, 0.9, { y: LY - 30 }, 'inOutCubic');
    tagA.to(T.handoff, 0.9, { y: 602 }, 'inOutCubic');
  });
})(window.Applicable = window.Applicable || {});
