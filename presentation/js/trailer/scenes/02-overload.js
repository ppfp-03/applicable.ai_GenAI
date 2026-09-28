/*
 * Phase 2 — Information overload (bars 6–11, 10–22 s).
 * Seen from above now, the desk keeps receiving: roles, deadlines, statuses, to-dos and files
 * fall out of the air and pile up in layers, faster and faster, while the camera slowly orbits.
 * Counters tally the load. On the beat everything stops dead: "And then it gets harder."
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function overload(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared, sfx, mood } = ctx;
    const r = A.rng(7);

    const pool = [];
    const cities = K.field.jobs.map((j) => j[3]);
    const closes = ['Closes in 2 d', 'Closes Fri', 'Closes 14 Oct', 'Closes in 5 d', 'Rolling', 'Closes 20 Oct', 'Closes tonight'];
    [0, 1].forEach((pass) =>
      K.field.jobs.forEach(([mono, title, company, city], i) => {
        const where = pass ? cities[(i + 7) % cities.length] : city;
        const k = i + pass * 5;
        pool.push(['job', C.jobCard({ mono, title, company, city: where, closes: closes[k % closes.length], hot: k % 4 === 0, grey: k % 3 === 1 })]);
      })
    );
    K.field.deadlines.forEach((d) => pool.push(['deadline', C.deadline(d)]));
    K.field.statuses.forEach((s) => pool.push(['status', C.status(s)]));
    K.field.reminders.forEach((s) => pool.push(['todo', C.reminder(s)]));
    K.field.documents.forEach((s) => pool.push(['document', C.fileChip(s)]));

    // Jittered grid around the desk, leaving the desk itself clear.
    const X0 = -900, X1 = 3200, Y0 = -700, Y1 = 1900, COLS = 15, ROWS = 9;
    const cw = (X1 - X0) / COLS, ch = (Y1 - Y0) / ROWS;
    const cells = [];
    for (let cy = 0; cy < ROWS; cy++) {
      for (let cx = 0; cx < COLS; cx++) {
        const x = X0 + (cx + 0.5) * cw, y = Y0 + (cy + 0.5) * ch;
        if (x > 700 && x < 1960 && y > 60 && y < 1080) continue;
        cells.push([x + (r() - 0.5) * cw * 0.5, y + (r() - 0.5) * ch * 0.45]);
      }
    }
    for (let i = cells.length - 1; i > 0; i--) {
      const j = Math.floor(r() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    const byType = {};
    pool.forEach((p) => (byType[p[0]] = byType[p[0]] || []).push(p));
    const order = [];
    const types = Object.keys(byType);
    while (order.length < pool.length) for (const k of types) if (byType[k].length) order.push(byType[k].shift());

    const centre = [1150, 620];
    const items = order.map(([type, el], i) => {
      const [x, y] = cells[i];
      return { type, el, x, y, d: Math.hypot(x - centre[0], (y - centre[1]) * 1.3) };
    });
    items.sort((a, b) => a.d - b.d);
    const N = items.length;
    items.forEach((it, k) => {
      // Arrivals accelerate: t = from + span·sqrt(k/N).
      it.tIn = T.fieldFrom + (T.fieldTo - T.fieldFrom) * Math.sqrt((k + 0.6) / N);
      it.r = (r() - 0.5) * 16;
      it.zRest = 4 + k * 0.7; // later arrivals rest on top of earlier ones
      it.el.classList.add('is-field');
      const spinY = (r() - 0.5) * 70, spinX = -30 - r() * 40;
      const a = place(it.el, world, { x: it.x + (r() - 0.5) * 160, y: it.y - 120, z: 900 + r() * 400, r: it.r + (r() - 0.5) * 60, rx: spinX, ry: spinY, o: 0 });
      a.to(it.tIn - 0.35, 0.2, { o: 1 }, 'linear');
      a.to(it.tIn - 0.35, 0.8, { x: it.x, y: it.y, z: it.zRest, r: it.r, rx: 0, ry: 0 }, 'outBack');
      // A slow slide on the table until the freeze: the desk never stops moving until it does.
      const vx = (r() - 0.5) * 22, vy = (r() - 0.5) * 16, vr = (r() - 0.5) * 1.4;
      const dt = T.freeze - (it.tIn + 0.45);
      it.x2 = it.x + vx * dt;
      it.y2 = it.y + vy * dt;
      it.r2 = it.r + vr * dt;
      a.to(it.tIn + 0.45, dt, { x: it.x2, y: it.y2, r: it.r2 }, 'linear');
      it.actor = a;
      if (k % 2 === 0) sfx(it.tIn + 0.05, 'drop', { k, gain: 0.35 + 0.4 * (k / N) });
    });
    shared.field = items;

    // The camera keeps rising and orbits; the stage cools.
    cam.to(T.repeat + 2.6, T.freeze - (T.repeat + 2.6), { s: 0.56, x: 1180, y: 620, rx: 52, ry: 14, r: -4 }, 'inOutSine');
    mood.to(T.fieldFrom, T.freeze - T.fieldFrom, { tense: 1 }, 'inSine');

    // Counters on a glass plate: what has landed on you.
    const counterKeys = [
      ['job', 'Open roles', 3],
      ['deadline', 'Deadlines', 0],
      ['status', 'Waiting on', 2],
      ['document', 'Documents', 4],
      ['todo', 'To-dos', 0],
    ];
    const bar = h('div.glass.counters');
    const nums = counterKeys.map(([, label]) => {
      const n = h('b', { text: '0' });
      bar.append(h('div.counter', null, n, h('span', { text: label })));
      return n;
    });
    const barA = place(bar, hud, { x: 110, y: 996, o: 0 }, { anchor: 'left' });
    barA.to(T.fieldFrom + 0.5, 0.6, { o: 1 }, 'outCubic').to(T.freeze + 0.1, 0.4, { o: 0 });
    const arrivals = counterKeys.map(([key]) => items.filter((it) => it.type === key).map((it) => it.tIn + 0.1));
    const lastN = nums.map(() => -1);
    ctx.tl.hook((t) => {
      if (t < T.fieldFrom || t > T.freeze + 1) return;
      counterKeys.forEach(([, , base], i) => {
        const v = base + arrivals[i].filter((x) => x <= t).length;
        if (v !== lastN[i]) nums[i].textContent = String((lastN[i] = v));
      });
    });

    const plate = h('div.glass.plate', null, h('div.hl-mask', null, h('div.hl-line', { text: K.overload })));
    const plateA = place(plate, hud, { x: 110, y: 878, o: 0, s: 0.98 }, { anchor: 'left' });
    plateA.to(T.overload, 0.5, { o: 1, s: 1 }, 'outCubic').to(T.freeze + 0.1, 0.4, { o: 0 });
    inner(plate.querySelector('.hl-line'), { y: 80 }).to(T.overload + 0.1, 0.7, { y: 0 }, 'outExpo');

    // Freeze: drift has stopped (tracks end on the beat); the desk recedes into grey.
    sfx(T.freeze, 'stop');
    cam.to(T.freeze, 0.12, { s: 0.575 }, 'outCubic').to(T.freeze + 0.12, 0.8, { o: 0.16 }, 'outCubic');

    const harder = C.headline(['And then it gets harder.'], 'center xl');
    const harderA = place(harder, hud, { x: 960, y: 540 });
    inner(harder.querySelector('.hl-line'), { y: 130 }).to(T.harder, 0.9, { y: 0 }, 'outExpo');
    harderA.to(T.dusk - 0.3, 0.45, { o: 0, s: 0.96 }, 'inCubic');
    sfx(T.harder, 'hit');
  });
})(window.Applicable = window.Applicable || {});
