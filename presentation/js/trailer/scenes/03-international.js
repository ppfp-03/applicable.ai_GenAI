/*
 * Phase 3 — The international student problem (bars 12–15, 22–30 s).
 * Dusk on the app's stage. The camera swoops down from above and picks one attractive role
 * up off the desk towards the lens; three constraints unfold beneath it like an accordion:
 * work authorization, language, visa / sponsorship. Pulling back up, every role on the desk
 * carries constraints of its own. "Do I like this job?" becomes "Can I actually apply?"
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function international(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared, sfx, mood } = ctx;
    const hero = ctx.tl.get(K.hero.id);
    const HX = 1325, HY = 232, HZ = 170;

    // Night falls on the stage.
    mood.to(T.dusk, 1.4, { night: 1, vig: 0.85 }, 'inOutSine');
    cam.to(T.dusk, 0.9, { o: 1 }, 'inOutSine');
    shared.field.forEach((it) => it.actor.to(T.dusk, 0.8, { o: 0.2 }, 'inOutSine'));
    const others = [shared.coreItems.jd, shared.coreItems.letter, shared.coreItems.form, ...shared.cvs, shared.jobs[0], shared.jobs[2]];
    others.forEach((a) => a.to(T.dusk, 0.8, { o: 0.2 }, 'inOutSine'));
    sfx(T.dusk, 'dusk');

    // Swoop down and pick the role up.
    const S = 1.7;
    cam.to(T.dusk + 0.1, 2.0, { s: S, x: HX - 290 / S, y: HY + 150, rx: 12, ry: -6, r: 0 }, 'inOutCubic');
    sfx(T.dusk + 0.1, 'whoosh', { d: 2.0, gain: 0.7 });
    hero.to(T.dusk + 0.9, 1.1, { z: HZ, rx: -8, r: 0 }, 'outCubic');

    const head = C.headline(K.abroad, 'xl');
    const headA = place(head, hud, { x: 110, y: 520 }, { anchor: 'left' });
    [...head.querySelectorAll('.hl-line')].forEach((ln, i) => {
      inner(ln, { y: 130 }).to(T.abroad + 0.4 + i * 0.35, 0.9, { y: 0 }, 'outExpo');
      sfx(T.abroad + 0.4 + i * 0.35, 'word', { i: i + 2 });
    });
    headA.to(T.fieldTags - 0.3, 0.5, { o: 0, x: 70 }, 'inCubic');

    // "Looks like a great fit." — the pull before the constraints.
    const like = h('span.chip.g.fitchip', { text: 'Looks like a great fit' });
    const likeA = place(like, world, { x: HX + 58, y: HY - 104, z: HZ + 10, rx: -8, o: 0, s: 0.8 });
    likeA.to(T.abroad + 1.2, 0.45, { o: 1, s: 1 }, 'outBack').to(T.question, 0.4, { o: 0 });
    sfx(T.abroad + 1.2, 'ding', { k: 2 });

    // Three constraints unfold, hinged at the top, one per bar-half.
    shared.constraints = K.constraints.map((c, i) => {
      const el = C.constraint(c);
      const y = HY + 86 + 12 + 29 + i * 66;
      const a = place(el, world, { x: HX, y, z: HZ, rx: -100, o: 0 }, null, 'constraint' + i);
      const t0 = T.constraints + i * T.constraintStep;
      a.to(t0, 0.12, { o: 1 }).to(t0, 0.7, { rx: -8 }, 'outBack');
      inner(el.querySelector('.ck'), { s: 1 }).to(t0 + 0.45, 0.16, { s: 1.4 }, 'outCubic').to(t0 + 0.61, 0.35, { s: 1 }, 'outBack');
      sfx(t0, 'constraint', { i });
      return a;
    });

    // Pull back up: every role now carries constraints.
    cam.to(T.fieldTags - 0.3, 2.3, { s: 0.48, x: 1170, y: 660, rx: 48, ry: -12, r: 3 }, 'inOutCubic');
    cam.to(T.fieldTags + 2.0, T.question - (T.fieldTags + 2.0), { ry: -17, s: 0.46 }, 'linear');
    sfx(T.fieldTags - 0.3, 'whoosh', { d: 2.3, gain: 0.8 });
    shared.field.forEach((it) => it.actor.to(T.fieldTags, 0.8, { o: it.type === 'job' ? 1 : 0.45 }, 'inOutSine'));
    [shared.jobs[0], shared.jobs[2]].forEach((a) => a.to(T.fieldTags, 0.8, { o: 1 }, 'inOutSine'));

    const tagged = shared.field.filter((it) => it.type === 'job').map((it) => ({ el: it.el, x: it.x2, y: it.y2 }));
    tagged.push({ el: shared.jobs[0].el, x: 1010, y: 232 }, { el: shared.jobs[2].el, x: 1640, y: 232 });
    let k = 0;
    tagged.forEach((it) => {
      const box = it.el.querySelector('.tags');
      const d = Math.hypot(it.x - HX, it.y - HY);
      const count = 1 + (k % 3 === 0 ? 1 : 0);
      for (let j = 0; j < count; j++) {
        const tag = C.tag(K.fieldTags[k++ % K.fieldTags.length]);
        box.append(tag);
        const t0 = T.fieldTags + 0.3 + d / 2400 + j * 0.12;
        inner(tag, { o: 0, s: 0.5, y: 12 }).to(t0, 0.4, { o: 1, s: 1, y: 0 }, 'outBack');
        if (k % 3 === 0) sfx(t0, 'tag', { k, gain: 0.5 });
      }
    });

    // Two questions, as a lower third.
    const scrim = place(h('div', { style: { width: '1920px', height: '420px', background: 'linear-gradient(to bottom, rgba(226,226,233,0), rgba(226,226,233,.94) 60%)' } }), hud, { x: 960, y: 880, o: 0 });
    scrim.to(T.like - 0.3, 0.8, { o: 1 }).to(T.question, 0.5, { o: 0 });
    const q1 = h('div.ask.soft', null, h('span.ck.g', { text: '✓' }), h('span', { text: K.like }));
    const q2 = h('div.ask.strong', null, h('span.ck.u', { text: '?' }), h('span', { text: K.can }));
    const q1A = place(q1, hud, { x: 110, y: 860, o: 0 }, { anchor: 'left' });
    const q2A = place(q2, hud, { x: 110, y: 960, o: 0 }, { anchor: 'left' });
    q1A.to(T.like, 0.6, { o: 1, y: 850 }, 'outCubic').to(T.can + 0.2, 0.5, { o: 0.5 }).to(T.question, 0.4, { o: 0 });
    q2A.to(T.can, 0.7, { o: 1, y: 950 }, 'outCubic').to(T.question, 0.4, { o: 0 });
    sfx(T.like, 'word', { i: 4 });
    sfx(T.can, 'sting');
  });
})(window.Applicable = window.Applicable || {});
