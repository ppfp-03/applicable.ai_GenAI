/*
 * Phase 3 — The international student problem (≈22–30 s).
 * Dusk falls. The camera finds one attractive role and three constraints attach to it:
 * work authorization, language, visa/sponsorship. Pulling back, every role on the desk now
 * carries constraints of its own — the most complex moment of the film.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function international(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared } = ctx;
    const hero = ctx.tl.get(K.hero.id);
    const HX = 1325, HY = 236; // the hero card's resting place (scene 1, "Compare")

    // Lights come back up on the frozen desk — at night.
    cam.to(T.dusk, 0.9, { o: 1 }, 'inOutSine');
    // Other things recede so the hero can be read.
    shared.field.forEach((it) => it.actor.to(T.dusk, 0.8, { o: 0.14 }, 'inOutSine'));
    const dimmed = [shared.coreItems.jd, shared.coreItems.letter, shared.coreItems.form, ...shared.cvs, shared.jobs[0], shared.jobs[2]];
    dimmed.forEach((a) => a.to(T.dusk, 0.8, { o: 0.14 }, 'inOutSine'));
    hero.cls(T.dusk, 'z-top');

    // Push in on the hero card, frame it right of centre.
    const S = 2.05;
    cam.to(T.dusk + 0.15, 1.9, { s: S, x: HX - 330 / S, y: HY + 100, r: 0 }, 'inOutCubic');

    const head = C.headline(['Now do it', 'in another country.'], 'left xl on-dark');
    const headA = place(head, hud, { x: 110, y: 520 }, { anchor: 'left' });
    [...head.querySelectorAll('.hl-line')].forEach((ln, i) =>
      inner(ln, { y: 130 }).to(T.abroad + 0.3 + i * 0.35, 0.9, { y: 0 }, 'outExpo')
    );
    headA.to(T.fieldTags - 0.2, 0.6, { o: 0, x: 80 }, 'inCubic');

    // "Looks like a great fit." — the pull before the constraints.
    const like = h('span.fitchip', null, h('b', { text: '✓' }), ' Looks like a great fit');
    const likeA = place(like, world, { x: HX + 60, y: HY - 92, o: 0, s: 0.8 });
    likeA.to(T.abroad + 1.2, 0.45, { o: 1, s: 1 }, 'outBack').to(T.question, 0.4, { o: 0 });

    // Three constraints attach beneath the card.
    shared.constraints = K.constraints.map((c, i) => {
      const el = C.constraint(c);
      const y = HY + 106 + i * 44;
      const a = place(el, world, { x: HX, y: y - 30, o: 0, s: 0.94 }, null, 'constraint' + i);
      const t0 = T.constraints + i * T.constraintStep;
      a.to(t0, 0.55, { y, o: 1, s: 1 }, 'outBack');
      a.cls(t0, 'z-top');
      inner(el.querySelector('.q'), { s: 1 })
        .to(t0 + 0.35, 0.18, { s: 1.35 }, 'outCubic')
        .to(t0 + 0.53, 0.35, { s: 1 }, 'outBack');
      return a;
    });

    // Pull back: everything else has constraints too.
    cam.to(T.fieldTags - 0.2, 2.1, { s: 0.5, x: 1150, y: 610, r: 0.8 }, 'inOutCubic');
    cam.to(T.fieldTags + 1.9, T.question - (T.fieldTags + 1.9), { s: 0.485, r: 1.1 }, 'linear');
    shared.field.forEach((it) => it.actor.to(T.fieldTags, 0.8, { o: it.type === 'job' ? 1 : 0.5 }, 'inOutSine'));
    [shared.jobs[0], shared.jobs[2]].forEach((a) => a.to(T.fieldTags, 0.8, { o: 1 }, 'inOutSine'));

    const tagged = shared.field.filter((it) => it.type === 'job').map((it) => ({ el: it.el, x: it.x2, y: it.y2 }));
    tagged.push({ el: shared.jobs[0].el, x: 1010, y: 236 }, { el: shared.jobs[2].el, x: 1640, y: 236 });
    let k = 0;
    tagged.forEach((it) => {
      const box = it.el.querySelector('.tags');
      const d = Math.hypot(it.x - HX, it.y - HY);
      const count = 1 + (k % 3 === 0 ? 1 : 0);
      for (let j = 0; j < count; j++) {
        const tag = C.tag(K.fieldTags[k++ % K.fieldTags.length]);
        box.append(tag);
        inner(tag, { o: 0, s: 0.6 }).to(T.fieldTags + 0.2 + d / 2600 + j * 0.12, 0.4, { o: 1, s: 1 }, 'outBack');
      }
    });

    // Two questions, as a lower third over a dusk scrim.
    const scrim = place(h('div.scrim'), hud, { x: 960, y: 880, o: 0 });
    scrim.to(T.like - 0.3, 0.8, { o: 1 }).to(T.question, 0.5, { o: 0 });
    const q1 = h('div.ask.soft', null, h('span.gl.go', { text: '✓' }), h('span', { text: K.like }));
    const q2 = h('div.ask.strong', null, h('span.gl.q', { text: '?' }), h('span', { text: K.can }));
    const q1A = place(q1, hud, { x: 110, y: 855, o: 0 }, { anchor: 'left' });
    const q2A = place(q2, hud, { x: 110, y: 955, o: 0 }, { anchor: 'left' });
    q1A.to(T.like, 0.6, { o: 1, y: 845 }, 'outCubic').to(T.can + 0.2, 0.5, { o: 0.45 }).to(T.question, 0.4, { o: 0 });
    q2A.to(T.can, 0.7, { o: 1, y: 945 }, 'outCubic').to(T.question, 0.4, { o: 0 });
  });
})(window.Applicable = window.Applicable || {});
