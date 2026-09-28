/*
 * Phase 2 — Information overload (≈12–22 s).
 * The camera keeps pulling back while roles, deadlines, statuses, reminders and files keep
 * arriving — faster and faster. Counters tally what you are now responsible for. Then
 * everything freezes mid-drift, and the world dims: "And then it gets harder."
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function overload(ctx) {
    const { T, content: K, C, h, world, hud, place, cam, shared } = ctx;
    const r = A.rng(7);

    // Build the item pool: [type, element].
    const pool = [];
    // Every role twice (another city the second time): the market is bigger than one list.
    const cities = K.field.jobs.map((j) => j[3]);
    [0, 1].forEach((pass) =>
      K.field.jobs.forEach(([mono, title, company, city], i) => {
        const where = pass ? cities[(i + 7) % cities.length] : city;
        pool.push(['job', C.jobCard({ mono, title, company, city: where, meta: ['Posted today', 'Posted 3 days ago', 'Posted 1 week ago'][(i + pass) % 3] })]);
      })
    );
    K.field.deadlines.forEach((d) => pool.push(['deadline', C.deadline(d)]));
    K.field.statuses.forEach((s) => pool.push(['status', C.status(s)]));
    K.field.reminders.forEach((s) => pool.push(['todo', C.reminder(s)]));
    K.field.documents.forEach((s) => pool.push(['document', C.fileChip(s)]));

    // Jittered grid around the desk, leaving the desk itself clear.
    const X0 = -880, X1 = 3180, Y0 = -560, Y1 = 1760, COLS = 15, ROWS = 9;
    const cw = (X1 - X0) / COLS, ch = (Y1 - Y0) / ROWS;
    const cells = [];
    for (let cy = 0; cy < ROWS; cy++) {
      for (let cx = 0; cx < COLS; cx++) {
        const x = X0 + (cx + 0.5) * cw, y = Y0 + (cy + 0.5) * ch;
        if (x > 60 && x < 1960 && y > 60 && y < 1080) continue;
        cells.push([x + (r() - 0.5) * cw * 0.45, y + (r() - 0.5) * ch * 0.4]);
      }
    }
    // Deterministic shuffle, then interleave types so no region is all one kind.
    for (let i = cells.length - 1; i > 0; i--) {
      const j = Math.floor(r() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    const order = [];
    const byType = {};
    pool.forEach((p) => (byType[p[0]] = byType[p[0]] || []).push(p));
    const types = Object.keys(byType);
    while (order.length < pool.length) for (const k of types) if (byType[k].length) order.push(byType[k].shift());

    const centre = [1080, 560];
    const items = order.map(([type, el], i) => {
      const [x, y] = cells[i];
      return { type, el, x, y, d: Math.hypot(x - centre[0], (y - centre[1]) * 1.6) };
    });
    // Nearest first, and arrivals accelerate: t = from + span·sqrt(k/N).
    items.sort((a, b) => a.d - b.d);
    const N = items.length;
    items.forEach((it, k) => {
      it.tIn = T.fieldFrom + (T.fieldTo - T.fieldFrom) * Math.sqrt((k + 0.6) / N);
      it.r = (r() - 0.5) * 12;
      const vx = (r() - 0.5) * 26, vy = (r() - 0.5) * 18, vr = (r() - 0.5) * 1.6;
      it.el.classList.add('is-field');
      const a = place(it.el, world, { x: it.x + vx * -0.6, y: it.y - 36, r: it.r - 4, o: 0, s: 1.1 });
      a.to(it.tIn, 0.55, { x: it.x, y: it.y, r: it.r, o: 1, s: 1 }, 'outCubic');
      // Slow drift until the freeze: the desk never stops moving until it suddenly does.
      const dt = T.freeze - (it.tIn + 0.55);
      it.x2 = it.x + vx * dt;
      it.y2 = it.y + vy * dt;
      it.r2 = it.r + vr * dt;
      a.to(it.tIn + 0.55, dt, { x: it.x2, y: it.y2, r: it.r2 }, 'linear');
      it.actor = a;
    });
    shared.field = items;

    cam.to(T.repeat + 2.2, T.freeze - (T.repeat + 2.2), { s: 0.46, x: 1150, y: 600, r: -1.2 }, 'inOutSine');

    // Counters: live tallies of what has landed on the desk.
    const counterKeys = [
      ['job', 'Open roles', 3],
      ['deadline', 'Deadlines', 0],
      ['status', 'Waiting on', 2],
      ['document', 'Documents', 4],
      ['todo', 'To-dos', 0],
    ];
    const bar = h('div.counters');
    const nums = counterKeys.map(([key, label]) => {
      const n = h('b', { text: '0' });
      bar.append(h('div.counter', null, n, h('span', { text: label })));
      return n;
    });
    const barA = place(bar, hud, { x: 110, y: 1000, o: 0 }, { anchor: 'left' });
    barA.to(T.fieldFrom + 0.6, 0.6, { o: 1 }, 'outCubic').to(T.freeze + 0.1, 0.5, { o: 0 });
    const arrivals = counterKeys.map(([key]) => items.filter((it) => it.type === key).map((it) => it.tIn + 0.3));
    const last = nums.map(() => -1);
    ctx.tl.hook((t) => {
      if (t < T.fieldFrom || t > T.freeze + 1) return;
      counterKeys.forEach(([, , base], i) => {
        const v = base + arrivals[i].filter((x) => x <= t).length;
        if (v !== last[i]) nums[i].textContent = String((last[i] = v));
      });
    });

    // "Too much to keep track of." on a paper plate, so it reads over the clutter.
    const plate = h('div.plate', null, h('div.hl-mask', null, h('div.hl-line', { text: K.overload })));
    const plateA = place(plate, hud, { x: 110, y: 890, o: 0, s: 0.98 }, { anchor: 'left' });
    plateA.to(T.overload, 0.5, { o: 1, s: 1 }, 'outCubic').to(T.freeze + 0.1, 0.5, { o: 0 });
    ctx.inner(plate.querySelector('.hl-line'), { y: 80 }).to(T.overload + 0.1, 0.7, { y: 0 }, 'outExpo');

    // Freeze: drift has already stopped (tracks end at T.freeze); now the world recedes.
    cam.to(T.freeze + 0.1, 0.6, { o: 0.14 }, 'outCubic');

    const harder = C.headline([K.harder], 'center xl');
    const harderA = place(harder, hud, { x: 960, y: 540 });
    ctx.inner(harder.querySelector('.hl-line'), { y: 130 }).to(T.harder, 0.9, { y: 0 }, 'outExpo');
    harderA.to(T.dusk - 0.35, 0.5, { o: 0, y: 500 }, 'inCubic');
  });
})(window.Applicable = window.Applicable || {});
