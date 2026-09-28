/*
 * Phase 5 — Applicable.ai organises the chaos (bars 17–22, 33.5–44 s).
 * Chaos was tilted; order is frontal. As the light reaches each object it lifts, straightens
 * and flies to its place: roles into one neat stack, the CV and the job post into two
 * panels. Each document is read, then turns over — its back is structured, sourced data.
 * Facts and requirements are matched, and a strong fit turns out to carry an explicit
 * conflict: fit and eligibility are different things.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function organise(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared, sfx, toScreen } = ctx;

    cam.to(T.organise, 2.2, { x: 960, y: 560, s: 1, rx: 0, ry: 0, r: 0 }, 'inOutCubic');
    sfx(T.organise, 'whoosh', { d: 2.2, gain: 0.6 });

    const PILE = [960, 912];
    const waveAt = (x, y) => {
      const [sx, sy] = toScreen(x, y, T.light);
      return T.organise + Math.min(1.4, Math.hypot(sx - 960, sy - 540) / 1100);
    };

    // Roles go to the stack (real thickness: each one a little higher); the rest is absorbed.
    let n = 0;
    const toPile = (a, x, y, isRole) => {
      const tw = waveAt(x, y);
      a.to(tw, 0.35, { r: 0, rx: 0, ry: 0, z: 140, o: 1 }, 'outCubic');
      if (isRole) {
        const i = n++;
        a.to(tw + 0.35, 0.95, { x: PILE[0], y: PILE[1] - Math.min(i, 12) * 1.6, z: 2 + i * 2.2, s: 0.62 }, 'inOutCubic');
        if (i % 4 === 0) sfx(tw + 1.25, 'stack', { i, gain: 0.5 });
      } else {
        a.to(tw + 0.35, 0.85, { x: PILE[0], y: PILE[1], z: 40, s: 0.3, o: 0 }, 'inOutCubic');
      }
      return tw;
    };
    shared.field.forEach((it) => {
      const tw = toPile(it.actor, it.x2, it.y2, it.type === 'job');
      const tags = it.el.querySelector('.tags');
      if (tags && tags.children.length) inner(tags, { o: 1 }).to(tw, 0.3, { o: 0 });
    });
    shared.jobs.forEach((a, i) => {
      const tw = toPile(a, [1010, 1325, 1640][i], 232, true);
      const tags = a.el.querySelector('.tags');
      if (tags && tags.children.length) inner(tags, { o: 1 }).to(tw, 0.3, { o: 0 });
      if (shared.slots[i]) shared.slots[i].to(tw, 0.3, { o: 0 });
    });
    toPile(shared.coreItems.letter, 1730, 616, false);
    toPile(shared.coreItems.form, 1240, 905, false);
    shared.constraints.forEach((a, i) => a.to(T.organise + i * 0.06, 0.5, { rx: -100, o: 0 }, 'inCubic'));

    const pileLabel = h('div.pile-label', null, h('b', { text: '62' }), ' opportunities, in one place');
    place(pileLabel, world, { x: PILE[0], y: PILE[1] + 80, z: 40, o: 0 }, null, 'pileLabel').to(T.panels + 0.8, 0.6, { o: 1 }, 'outCubic');

    // --- The two documents become two flip panels.
    const PW = 560, PH = 560;
    const makeFlip = (id, x, front, back) => {
      const box = h('div.flip.d3', { style: { width: PW + 'px', height: PH + 'px' } });
      const f = h('div.face.front', { style: { display: 'grid', placeItems: 'center' } }, front);
      const b = h('div.face.back', null, back);
      box.append(f, b);
      const a = place(box, world, { x, y: 560, o: 0 }, null, id);
      // The back face's rotateY(180°) lives in its actor (an actor owns the whole transform).
      return { a, f, b, frontA: inner(f, { o: 1 }), backA: inner(b, { o: 1, ry: 180 }) };
    };

    const cvFront = C.cvDoc(K.cvFiles[2], 50);
    const facts = K.facts.map(C.fact);
    const cvBack = C.panel('Read from your CV', K.profileTitle, K.profileSub, facts);
    const L = makeFlip('flipCv', 430, cvFront, cvBack);

    const jdFront = C.jobDoc(K.jd);
    const reqs = K.requirements.map(C.requirement);
    const jdBack = C.panel('Read from the job post', K.requirementsTitle, K.requirementsSub, reqs);
    const R = makeFlip('flipJd', 1490, jdFront, jdBack);
    [cvBack, jdBack].forEach((p) => (p.style.width = PW + 'px'));

    // Old documents fly over and hand off to the panels' fronts (identical, so the swap is invisible).
    const cv = ctx.tl.get('cv'), jd = ctx.tl.get('jd');
    [ctx.tl.get('cv0'), ctx.tl.get('cv1')].forEach((a) => a.to(T.organise, 0.8, { x: 1470, y: 684, z: 20, r: 6, o: 0 }, 'inOutCubic'));
    cv.to(T.organise + 0.3, 1.2, { x: 430, y: 560, z: 0, s: 1, r: 0, rx: 0, ry: 0, o: 1 }, 'inOutCubic').set(T.panels, { o: 0 });
    jd.to(T.organise + 0.3, 1.2, { x: 1490, y: 560, z: 0, s: 1, r: 0, rx: 0, ry: 0, o: 1 }, 'inOutCubic').set(T.panels, { o: 0 });
    L.a.set(T.panels, { o: 1 });
    R.a.set(T.panels, { o: 1 });

    // Read, then turn over.
    const scan = (docEl, t0, height) => {
      inner(docEl.querySelector('.scan'), { y: 0, o: 0 }).to(t0, 0.12, { o: 1 }).to(t0, 0.75, { y: height + 48 }, 'inOutSine').to(t0 + 0.75, 0.12, { o: 0 });
      sfx(t0, 'scan', { d: 0.75 });
    };
    const flip = (F, t0, rows, prefix) => {
      F.a.to(t0, 1.0, { ry: 180 }, 'inOutCubic');
      F.a.to(t0, 0.5, { z: 160 }, 'outCubic').to(t0 + 0.5, 0.5, { z: 0 }, 'inCubic');
      sfx(t0, 'flip');
      rows.forEach((el, i) => {
        const ra = inner(el, { o: 0, x: -18 }, null, prefix + i);
        ra.to(t0 + 0.75 + i * 0.09, 0.45, { o: 1, x: 0 }, 'outCubic');
        sfx(t0 + 0.75 + i * 0.09, 'row', { i, gain: 0.55 });
      });
    };
    scan(cvFront, T.flipCv - 0.85, 400);
    flip(L, T.flipCv, facts, 'fact');
    scan(jdFront, T.flipJd - 0.85, 450);
    flip(R, T.flipJd, reqs, 'req');

    // The method, top-right (the lockup holds the top-left).
    const trio = h('div.trio', null, ...K.method.map((m) => h('span', { text: m })));
    const trioA = place(trio, hud, { x: 1864, y: 58, o: 1 }, { anchor: 'none' }, 'trio');
    trio.style.transform = '';
    trio.style.translate = '-100% -50%';
    const words = [...trio.children].map((s) => inner(s, { o: 0, y: 20 }));
    shared.trio = { trioA, words };
    words[0].to(T.understand, 0.6, { o: 1, y: 0 }, 'outCubic');
    sfx(T.understand, 'word', { i: 7 });

    // Matching: a line per requirement from the fact it is checked against.
    // Row centres are measured once layout exists (see trailer.js: actor.lazyY).
    const rowY = (rowEl) => 560 - PH / 2 + rowEl.offsetTop + rowEl.offsetHeight / 2;
    const links = [];
    K.requirements.forEach((r, i) => {
      if (r.match == null) return;
      const line = h('div.link.is-' + r.status);
      const t0 = T.links + links.length * T.linkStep;
      const a = place(line, world, { x: 430 + PW / 2, y: 560, z: 1, sx: 0 }, { anchor: 'left' }, 'link' + i);
      a.lazyY = () => rowY(reqs[i]);
      line.style.width = 1490 - PW / 2 - (430 + PW / 2) + 'px';
      a.to(t0, 0.45, { sx: 1 }, 'inOutCubic');
      ctx.tl.get('req' + i).cls(t0 + 0.4, 'show-state');
      sfx(t0 + 0.4, r.status === 'conflict' ? 'conflict' : 'met', { i });
      links.push(a);
      if (r.status === 'conflict') {
        const lbl = h('span.chip.r.nodot', null, 'German A2 · C1 required');
        const la = place(lbl, world, { x: 960, y: 560, z: 2, o: 0, s: 0.8 }, null, 'conflictLabel');
        la.lazyY = () => rowY(reqs[i]);
        la.to(t0 + 0.45, 0.45, { o: 1, s: 1 }, 'outBack');
      }
    });

    // Fit and eligibility, side by side — not the same thing.
    const fit = place(C.summaryChip(K.fitLabel, K.fitValue, 'fit'), world, { x: 1352, y: 900, z: 4, o: 0, rx: -60 }, null, 'fitChip');
    const elig = place(C.summaryChip(K.eligLabel, K.eligValue, 'conflict'), world, { x: 1628, y: 900, z: 4, o: 0, rx: -60 }, null, 'eligChip');
    fit.to(T.verdictSplit, 0.6, { o: 1, rx: 0 }, 'outBack');
    elig.to(T.verdictSplit + 0.5, 0.6, { o: 1, rx: 0 }, 'outBack');
    sfx(T.verdictSplit, 'card', { gain: 0.6 });
    sfx(T.verdictSplit + 0.5, 'conflict', { i: 9 });
    const note = h('div.side-note', { text: 'A strong fit can still be a hard no.' });
    place(note, world, { x: 150, y: 900, z: 4, o: 0 }, { anchor: 'left' }, 'sideNote').to(T.verdictSplit + 1.0, 0.7, { o: 1 }, 'outCubic');
    sfx(T.verdictSplit + 1.0, 'word', { i: 8 });

    shared.panels = { L, R, facts, reqs, links, fit, elig, PILE };
    shared.lazy = [...links, ctx.tl.get('conflictLabel')];
  });
})(window.Applicable = window.Applicable || {});
