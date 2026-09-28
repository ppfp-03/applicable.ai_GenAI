/*
 * Phase 6 — From information to decision (bars 23–26, 44–52 s).
 * Four roles lift off the stack, first sorted by fit alone. Eligibility is checked row by
 * row: the best fit has an explicit conflict and sinks back into "Not for now" (still
 * visible, never hidden). One role needs verification — instead of guessing, Applicable.ai
 * asks one question. The answer arrives, the list recomputes, and that role rises to #1.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function decide(ctx) {
    const { T, content: K, C, h, world, place, inner, shared, tl, sfx } = ctx;
    const P = shared.panels;

    // The panels step back and fade; their meaning moves into the rows.
    [P.L, P.R].forEach((F, k) => {
      F.a.to(T.list - 0.4, 0.9, { z: -260, x: F.a.v('x') + (k ? 160 : -160) }, 'inCubic');
      F.backA.to(T.list - 0.3, 0.6, { o: 0 });
    });
    P.links.forEach((a) => a.to(T.list - 0.4, 0.4, { o: 0 }));
    ['conflictLabel', 'sideNote', 'pileLabel'].forEach((id) => tl.get(id).to(T.list - 0.2, 0.45, { o: 0 }));
    P.fit.to(T.list - 0.2, 0.7, { x: 1400, y: 330, z: 60, s: 0.5, o: 0 }, 'inOutCubic');
    P.elig.to(T.list - 0.2, 0.7, { x: 1400, y: 330, z: 60, s: 0.5, o: 0 }, 'inOutCubic');
    sfx(T.list - 0.4, 'whoosh', { d: 1.0, gain: 0.5 });

    // The stack sinks away; four of its roles lift off and become rows.
    shared.field.forEach((it) => {
      if (it.type === 'job') it.actor.to(T.list + 0.3, 0.7, { y: 1250, z: -200, o: 0 }, 'inCubic');
    });
    shared.jobs.forEach((a) => a.to(T.list + 0.2, 0.5, { o: 0 }, 'inCubic'));

    const title = h('div.list-title', null, h('b', { text: 'Sorted by fit' }), ' · 4 of 62');
    const titleA = place(title, world, { x: 390, y: 250, o: 0 }, { anchor: 'left' }, 'listTitle');
    titleA.to(T.list + 0.3, 0.5, { o: 1 }, 'outCubic');
    titleA.text(T.demote + 0.4, 'Eligible first, then by priority', title.querySelector('b'));
    titleA.text(T.prioritise, K.listTitleAfter, title.querySelector('b'));

    const Y = (slot) => 340 + slot * 122;
    const rows = {};
    K.ranking.forEach((r, i) => {
      const el = C.rankRow(r);
      const a = place(el, world, { x: 960, y: P.PILE[1], z: 40, s: 0.55, rx: -70, o: 0 }, null, r.id);
      const t0 = T.list + 0.15 + i * 0.13;
      a.to(t0, 0.15, { o: 1 }).to(t0, 0.9, { y: Y(i), z: 0, s: 1, rx: 0 }, 'outBack');
      sfx(t0 + 0.5, 'row', { i: i + 2, gain: 0.7 });
      const R = { a, el, n: el.querySelector('.rank-n span'), v: el.querySelector('.verdict'), vt: el.querySelector('.vt'), vd: el.querySelector('.vdetail') };
      rows[r.id] = R;
      a.text(-1, String(i + 1), R.n);
      a.text(-1, K.checking, R.vt);
      a.cls(-1, 'v-checking');
    });

    // Eligibility resolves, row by row, on the beat.
    const setStatus = (id, t, kind, text, detail) => {
      const R = rows[id];
      R.a.text(t, text, R.vt);
      R.a.text(t, detail || '', R.vd);
      ['go', 'clarify', 'skip', 'checking'].forEach((k) => R.a.cls(t, 'v-' + k, k === kind));
      R.pop = R.pop || inner(R.v, { s: 1 });
      R.pop.to(t, 0.1, { s: 0.88 }, 'outCubic').to(t + 0.1, 0.4, { s: 1 }, 'outBack');
      sfx(t, kind === 'skip' ? 'conflict' : kind === 'clarify' ? 'verify' : 'met', { i: 5 + Object.keys(rows).indexOf(id) });
    };
    setStatus('r-deutsch', T.statuses, 'skip', K.status.conflict, K.statusDetail['r-deutsch']);
    setStatus('r-bolton', T.statuses + T.statusStep, 'clarify', K.status.verify, K.statusDetail['r-bolton']);
    setStatus('r-nestella', T.statuses + 2 * T.statusStep, 'go', K.status.eligible);
    setStatus('r-unicreda', T.statuses + 3 * T.statusStep, 'go', K.status.eligible);

    // The conflict sinks back under "Not for now"; needs-verification sits below eligible.
    const D = rows['r-deutsch'].a, B = rows['r-bolton'].a, N = rows['r-nestella'].a, U = rows['r-unicreda'].a;
    const divider = h('div.divider', null, h('span', { text: K.notForNow }));
    const divA = place(divider, world, { x: 960, y: Y(3) - 28, o: 0 }, null, 'divider');
    D.to(T.demote, 0.45, { z: -90 }, 'inCubic').to(T.demote + 0.45, 0.7, { y: Y(3) + 46, z: -30 }, 'outCubic');
    D.cls(T.demote + 0.3, 'is-muted');
    [
      [N, 0],
      [U, 1],
      [B, 2],
    ].forEach(([a, slot], k) => a.to(T.demote + 0.1 + k * 0.05, 0.4, { z: 50 }, 'outCubic').to(T.demote + 0.5 + k * 0.05, 0.7, { y: Y(slot), z: 0 }, 'inOutCubic'));
    divA.to(T.demote + 0.5, 0.4, { o: 1 }, 'outCubic');
    sfx(T.demote, 'sink');
    const rank = (t, order) => order.forEach(([id, label]) => rows[id].a.text(t, label, rows[id].n));
    rank(T.demote + 0.6, [['r-nestella', '1'], ['r-unicreda', '2'], ['r-bolton', '3'], ['r-deutsch', '–']]);

    // Verify: one question, asked in place.
    shared.trio.words[0].to(T.verify, 0.4, { o: 0.35 });
    shared.trio.words[1].to(T.verify, 0.6, { o: 1, y: 0 }, 'outCubic');
    sfx(T.verify, 'word', { i: 9 });
    [N, U, D, divA].forEach((a) => a.to(T.ask, 0.4, { o: a === D ? 0.3 : 0.4 }));
    const q = C.question(K.clarify);
    const qA = place(q, world, { x: 1240, y: Y(2) + 150, z: 90, ry: -80, o: 0 }, null, 'question');
    qA.to(T.ask, 0.15, { o: 1 }).to(T.ask, 0.8, { ry: 0 }, 'outBack');
    sfx(T.ask, 'question');
    const chosenA = inner(q.querySelector('.is-chosen'), { s: 1 });
    chosenA.cls(T.answer, 'is-picked');
    chosenA.to(T.answer - 0.08, 0.1, { s: 0.9 }, 'outCubic').to(T.answer + 0.02, 0.3, { s: 1 }, 'outBack');
    sfx(T.answer, 'click');
    qA.to(T.answer + 0.4, 0.45, { o: 0, s: 0.4, x: 1300, y: Y(2), z: 20, rx: 30 }, 'inCubic');

    // Recompute: verified, and it rises to #1 — lifted towards us, over the others.
    setStatus('r-bolton', T.recompute, 'go', K.status.eligible, 'You answered · right to work in the UK');
    const delta = h('span.delta', { text: K.moved });
    const deltaA = place(delta, world, { x: 1596, y: Y(2) - 40, z: 140, o: 0, s: 0.7 }, null, 'delta');
    deltaA.to(T.recompute + 0.15, 0.4, { o: 1, s: 1 }, 'outBack');
    B.to(T.recompute, 0.35, { z: 130, s: 1.03 }, 'outCubic').to(T.recompute + 0.35, 0.9, { y: Y(0) }, 'inOutCubic').to(T.recompute + 1.25, 0.45, { z: 0, s: 1 }, 'outBack');
    deltaA.to(T.recompute + 0.35, 0.9, { y: Y(0) - 40 }, 'inOutCubic').to(T.focus - 0.5, 0.4, { o: 0 });
    N.to(T.recompute + 0.4, 0.85, { y: Y(1), o: 1 }, 'inOutCubic');
    U.to(T.recompute + 0.45, 0.85, { y: Y(2), o: 1 }, 'inOutCubic');
    D.to(T.recompute + 0.45, 0.6, { o: 0.75 });
    divA.to(T.recompute + 0.45, 0.6, { o: 1 });
    rank(T.recompute + 0.8, [['r-bolton', '1'], ['r-nestella', '2'], ['r-unicreda', '3']]);
    sfx(T.recompute + 0.3, 'rise');

    shared.trio.words[1].to(T.prioritise, 0.4, { o: 0.35 });
    shared.trio.words[2].to(T.prioritise, 0.6, { o: 1, y: 0 }, 'outCubic');
    sfx(T.prioritise, 'word', { i: 10 });

    shared.rows = { D, B, N, U, divA, titleA, Y };
  });
})(window.Applicable = window.Applicable || {});
