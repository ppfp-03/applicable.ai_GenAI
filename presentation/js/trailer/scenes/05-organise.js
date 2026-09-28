/*
 * Phase 5 — Applicable.ai organises the chaos (≈33–44 s).
 * As the daylight wave reaches each object, it straightens and goes where it belongs:
 * roles into one neat pile, the CV and the job post into two panels. Each document is read
 * and collapses into sourced facts. Facts and requirements are matched — and a strong fit
 * turns out to carry an explicit conflict. Fit and eligibility are different things.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function organise(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared, toScreen } = ctx;

    cam.to(T.organise + 0.1, 2.0, { x: 960, y: 560, s: 1.12, r: 0 }, 'inOutCubic');

    const PILE = [960, 922];
    const waveAt = (x, y) => {
      const [sx, sy] = toScreen(x, y, T.light);
      return T.organise + Math.hypot(sx - 960, sy - 540) / 1250;
    };

    // Everything that is a role goes to the pile; everything else is absorbed into it.
    let n = 0;
    const toPile = (a, x, y, isRole) => {
      const tw = waveAt(x, y);
      a.cls(tw, 'z-top', false);
      a.to(tw, 0.35, { r: 0 }, 'outCubic');
      if (isRole) {
        const i = n++;
        const lift = Math.min(i, 9) * 2.4;
        a.to(tw + 0.2, 1.05, { x: PILE[0], y: PILE[1] - lift, s: 0.62, o: 1 }, 'inOutCubic');
        a.cls(tw + 0.2, 'is-piled');
      } else {
        a.to(tw + 0.2, 0.95, { x: PILE[0], y: PILE[1], s: 0.3, o: 0 }, 'inOutCubic');
      }
      return tw;
    };

    shared.field.forEach((it) => {
      const tw = toPile(it.actor, it.x2, it.y2, it.type === 'job');
      const tags = it.el.querySelector('.tags');
      if (tags) inner(tags, { o: 1 }).to(tw, 0.3, { o: 0 });
    });
    shared.jobs.forEach((a, i) => {
      const x = [1010, 1325, 1640][i];
      const tw = toPile(a, x, 236, true);
      inner(a.el.querySelector('.tags'), { o: 1 }).to(tw, 0.3, { o: 0 });
      const slot = a.el.querySelector('.status-slot');
      if (slot.textContent) inner(slot.parentElement, { o: 1 }).to(tw, 0.3, { o: 0 });
    });
    toPile(shared.coreItems.letter, 1720, 610, false);
    toPile(shared.coreItems.form, 1215, 905, false);
    shared.constraints.forEach((a, i) => {
      a.cls(T.organise, 'z-top', false);
      a.to(T.organise + 0.2, 1.0, { x: 1490, y: 470 + i * 68, o: 0, s: 0.9 }, 'inOutCubic');
    });

    const pileLabel = h('div.pile-label', null, h('b', { text: '62' }), ' opportunities, in one place');
    place(pileLabel, world, { x: PILE[0], y: PILE[1] + 78, o: 0 }, null, 'pileLabel').to(T.panels + 0.6, 0.6, { o: 1 }, 'outCubic');

    // The CV versions consolidate into one, which moves to the left panel.
    const [cv0, cv1] = [ctx.tl.get('cv0'), ctx.tl.get('cv1')];
    const cv = ctx.tl.get('cv');
    const jd = ctx.tl.get('jd');
    [cv0, cv1].forEach((a) => a.to(T.organise + 0.1, 0.9, { x: 1460, y: 664, r: 6, o: 0 }, 'inOutCubic'));
    cv.cls(T.organise, 'z-top');
    jd.cls(T.organise, 'z-top');
    cv.to(T.organise + 0.85, 1.35, { x: 430, y: 520, s: 1.25, r: 0, o: 1 }, 'inOutCubic');
    jd.to(T.organise + 0.9, 1.35, { x: 1490, y: 520, s: 1.25, r: 0, o: 1 }, 'inOutCubic');

    // Reading: a thin AI-blue line scans each document.
    const scan = (docA, t0, height) => {
      const s = inner(docA.el.querySelector('.scan'), { y: 0, o: 0 });
      s.to(t0, 0.15, { o: 1 }).to(t0, 0.85, { y: height }, 'inOutSine').to(t0 + 0.85, 0.15, { o: 0 });
    };
    scan(cv, T.scanCv, 386);
    scan(jd, T.scanJd, 436);

    const ROW0 = 300, STEP = 68;
    const rowsFrom = (docA, t0, x, items, factory, idPrefix) => {
      docA.to(t0, 0.5, { o: 0, s: 1.18, sy: 0.9 }, 'inCubic');
      return items.map((item, i) => {
        const el = factory(item);
        const a = place(el, world, { x, y: 520, o: 0, s: 0.92 }, null, idPrefix + i);
        a.to(t0 + 0.1 + i * 0.09, 0.65, { y: ROW0 + i * STEP, o: 1, s: 1 }, 'outCubic');
        return a;
      });
    };

    const lHead = C.panelHead('Read from your CV', K.profileTitle);
    place(lHead, world, { x: 160, y: 215, o: 0 }, { anchor: 'left' }, 'lHead').to(T.facts, 0.6, { o: 1 }, 'outCubic');
    const facts = rowsFrom(cv, T.facts, 430, K.facts, C.fact, 'fact');

    const rHead = C.panelHead('Read from the job post', K.requirementsTitle, K.requirementsSub);
    place(rHead, world, { x: 1220, y: 205, o: 0 }, { anchor: 'left' }, 'rHead').to(T.reqs, 0.6, { o: 1 }, 'outCubic');
    const reqs = rowsFrom(jd, T.reqs, 1490, K.requirements, C.requirement, 'req');

    // The method, bottom-left: Understand. Verify. Prioritise.
    const trio = h('div.trio', null, ...K.method.map((m) => h('span', { text: m })));
    const trioA = place(trio, hud, { x: 110, y: 1005, o: 1 }, { anchor: 'left' }, 'trio');
    const words = [...trio.children].map((s) => inner(s, { o: 0, y: 24 }));
    shared.trio = { trioA, words };
    words[0].to(T.understand, 0.6, { o: 1, y: 0 }, 'outCubic');

    // Matching: a line per requirement, drawn from the fact it is checked against.
    const links = [];
    K.requirements.forEach((r, i) => {
      if (r.match == null) return;
      const y = ROW0 + i * STEP;
      const line = h('div.link.is-' + r.status);
      const t0 = T.links + links.length * 0.28;
      const a = place(line, world, { x: 700, y, sx: 0 }, { anchor: 'left' }, 'link' + i);
      a.to(t0, 0.45, { sx: 1 }, 'inOutCubic');
      reqs[i].cls(t0 + 0.4, 'show-state');
      facts[r.match].cls(t0, 'is-linked');
      links.push(a);
      if (r.status === 'conflict') {
        const lbl = h('span.link-label', null, 'German ', h('b', { text: 'A2' }), ' · ', h('b', { text: 'C1' }), ' required');
        const la = place(lbl, world, { x: 960, y: y - 1, o: 0, s: 0.8 }, null, 'conflictLabel');
        la.to(t0 + 0.45, 0.45, { o: 1, s: 1 }, 'outBack');
      }
    });

    // Fit and eligibility, side by side, and not the same thing.
    const fit = place(C.summaryChip(K.fitLabel, K.fitValue, 'fit'), world, { x: 1355, y: 742, o: 0 }, null, 'fitChip');
    const elig = place(C.summaryChip(K.eligLabel, K.eligValue, 'conflict'), world, { x: 1628, y: 742, o: 0 }, null, 'eligChip');
    fit.to(T.verdictSplit, 0.5, { o: 1 }, 'outCubic');
    elig.to(T.verdictSplit + 0.45, 0.5, { o: 1 }, 'outCubic');
    const note = h('div.side-note', { text: 'A strong fit can still be a hard no.' });
    place(note, world, { x: 160, y: 742, o: 0 }, { anchor: 'left' }, 'sideNote').to(T.verdictSplit + 0.9, 0.7, { o: 1 }, 'outCubic');

    shared.panels = { facts, reqs, links, lHead, rHead, fit, elig };
  });
})(window.Applicable = window.Applicable || {});
