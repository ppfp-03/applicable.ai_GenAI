/*
 * Phase 6 — From information to decision (≈44–52 s).
 * The pile deals four roles, first sorted by fit alone. Eligibility is checked: the best fit
 * has an explicit conflict and steps down into "Not for now" (visible, never hidden). One
 * role needs verification — instead of guessing, Applicable.ai asks one question. The
 * answer arrives, the list recomputes, and that role becomes #1.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function decide(ctx) {
    const { T, content: K, C, h, world, place, inner, shared, tl } = ctx;
    const P = shared.panels;

    // Clear the panels: facts slide away left, requirements fold into their role's row.
    P.facts.forEach((a, i) => a.to(T.list - 0.2 + i * 0.05, 0.6, { x: 330, o: 0 }, 'inCubic'));
    P.reqs.forEach((a, i) => a.to(T.list - 0.2 + i * 0.05, 0.7, { x: 960, y: 330, s: 0.6, o: 0 }, 'inOutCubic'));
    P.links.forEach((a) => a.to(T.list - 0.3, 0.4, { o: 0 }));
    ['lHead', 'rHead', 'conflictLabel', 'sideNote', 'pileLabel'].forEach((id) => tl.get(id).to(T.list - 0.3, 0.45, { o: 0 }));
    P.fit.to(T.list - 0.1, 0.7, { x: 1250, y: 330, s: 0.6, o: 0 }, 'inOutCubic');
    P.elig.to(T.list - 0.1, 0.7, { x: 1450, y: 330, s: 0.6, o: 0 }, 'inOutCubic');

    // Piled roles sink away; four of them become rows.
    shared.field.forEach((it) => {
      if (it.type === 'job') it.actor.to(T.list + 0.3, 0.6, { y: 1180, o: 0 }, 'inCubic');
    });
    shared.jobs.forEach((a) => a.to(T.list + 0.2, 0.5, { o: 0 }, 'inCubic'));

    const title = h('div.list-title', { text: K.listTitleBefore });
    const titleA = place(title, world, { x: 380, y: 262, o: 0 }, { anchor: 'left' }, 'listTitle');
    titleA.to(T.list + 0.3, 0.5, { o: 1 }, 'outCubic');
    titleA.text(T.prioritise, K.listTitleAfter);

    const Y = (slot) => 340 + slot * 118;
    const rows = {};
    K.ranking.forEach((r, i) => {
      const el = C.rankRow(r);
      const a = place(el, world, { x: 960, y: 922, s: 0.55, o: 0 }, null, r.id);
      a.to(T.list + 0.15 + i * 0.12, 0.85, { y: Y(i), s: 1, o: 1 }, 'outCubic');
      rows[r.id] = { a, el, n: el.querySelector('.rank-n span'), v: el.querySelector('.verdict'), vt: el.querySelector('.vt'), vd: el.querySelector('.vdetail') };
      a.text(-1, String(i + 1), rows[r.id].n);
      a.text(-1, K.checking, rows[r.id].vt);
    });

    // Eligibility resolves row by row.
    const setStatus = (id, t, kind, text, detail) => {
      const R = rows[id];
      R.a.text(t, text, R.vt);
      R.a.text(t, detail || '', R.vd);
      ['go', 'clarify', 'skip', 'checking'].forEach((k) => R.a.cls(t, 'v-' + k, k === kind));
      R.pop = R.pop || inner(R.v, { s: 1 });
      R.pop.to(t, 0.12, { s: 0.9 }, 'outCubic').to(t + 0.12, 0.35, { s: 1 }, 'outBack');
    };
    K.ranking.forEach((r) => rows[r.id].a.cls(-1, 'v-checking'));
    setStatus('r-deutsch', T.statuses, 'skip', K.status.conflict, K.statusDetail['r-deutsch']);
    setStatus('r-bolton', T.statuses + 0.3, 'clarify', K.status.verify, K.statusDetail['r-bolton']);
    setStatus('r-nestella', T.statuses + 0.6, 'go', K.status.eligible);
    setStatus('r-unicreda', T.statuses + 0.85, 'go', K.status.eligible);

    // The conflict steps down under "Not for now"; needs-verification sits below eligible.
    const D = rows['r-deutsch'].a, B = rows['r-bolton'].a, N = rows['r-nestella'].a, U = rows['r-unicreda'].a;
    const divider = h('div.divider', null, h('span', { text: K.notForNow }));
    const divA = place(divider, world, { x: 960, y: Y(3) - 30, o: 0 }, null, 'divider');
    D.to(T.demote, 0.9, { y: Y(3) + 40 }, 'inOutCubic');
    D.cls(T.demote + 0.3, 'is-muted');
    N.to(T.demote + 0.1, 0.8, { y: Y(0) }, 'inOutCubic');
    U.to(T.demote + 0.15, 0.8, { y: Y(1) }, 'inOutCubic');
    B.to(T.demote + 0.1, 0.8, { y: Y(2) }, 'inOutCubic');
    divA.to(T.demote + 0.5, 0.5, { o: 1 }, 'outCubic');
    const rank = (t, order) => order.forEach(([id, label]) => rows[id].a.text(t, label, rows[id].n));
    rank(T.demote + 0.4, [['r-nestella', '1'], ['r-unicreda', '2'], ['r-bolton', '3'], ['r-deutsch', '–']]);

    // Verify: one question, asked in place.
    shared.trio.words[0].to(T.verify, 0.4, { o: 0.35 });
    shared.trio.words[1].to(T.verify, 0.6, { o: 1, y: 0 }, 'outCubic');
    [N, U, D, divA].forEach((a) => a.to(T.ask - 0.1, 0.4, { o: a === D ? 0.3 : 0.4 }));
    const q = C.question(K.clarify);
    const qA = place(q, world, { x: 1210, y: Y(2) + 140, o: 0, s: 0.92 }, null, 'question');
    qA.to(T.ask, 0.55, { o: 1, s: 1, y: Y(2) + 126 }, 'outBack');
    const chosen = q.querySelector('.is-chosen');
    const chosenA = inner(chosen, { s: 1 });
    chosenA.cls(T.answer, 'is-picked');
    chosenA.to(T.answer - 0.08, 0.1, { s: 0.92 }, 'outCubic').to(T.answer + 0.02, 0.3, { s: 1 }, 'outBack');
    qA.to(T.answer + 0.45, 0.4, { o: 0, s: 0.4, x: 1330, y: Y(2) }, 'inCubic');

    // Recompute: verified, moves to #1.
    setStatus('r-bolton', T.recompute, 'go', K.status.eligible, 'You answered · UK right to work');
    const delta = h('span.delta', { text: K.moved });
    const deltaA = place(delta, world, { x: 1640, y: Y(2) - 30, o: 0, s: 0.7 }, null, 'delta');
    deltaA.to(T.recompute + 0.15, 0.4, { o: 1, s: 1 }, 'outBack');
    B.cls(T.recompute, 'is-pop');
    B.cls(T.recompute, 'z-top');
    B.to(T.recompute, 0.3, { s: 1.03 }, 'outCubic').to(T.recompute + 1.25, 0.4, { s: 1 }, 'inOutCubic');
    B.to(T.recompute + 0.3, 0.95, { y: Y(0) }, 'inOutCubic');
    deltaA.to(T.recompute + 0.3, 0.95, { y: Y(0) - 30 }, 'inOutCubic').to(T.focus - 0.4, 0.4, { o: 0 });
    N.to(T.recompute + 0.35, 0.9, { y: Y(1), o: 1 }, 'inOutCubic');
    U.to(T.recompute + 0.4, 0.9, { y: Y(2), o: 1 }, 'inOutCubic');
    D.to(T.recompute + 0.4, 0.6, { o: 0.75 });
    divA.to(T.recompute + 0.4, 0.6, { o: 1 });
    rank(T.recompute + 0.7, [['r-bolton', '1'], ['r-nestella', '2'], ['r-unicreda', '3']]);

    shared.trio.words[1].to(T.prioritise, 0.4, { o: 0.35 });
    shared.trio.words[2].to(T.prioritise, 0.6, { o: 1, y: 0 }, 'outCubic');

    shared.rows = { D, B, N, U, divA, titleA, Y };
  });
})(window.Applicable = window.Applicable || {});
