/*
 * Phase 1 — The normal application problem (bars 1–5, 0–10 s).
 * One sentence on the app's calm stage. Then the camera tilts down onto a desk and seven
 * verbs turn over on a drum; each verb drops its own object onto the table, so the workload
 * piles up. On "Repeat." the drum spins through the whole loop again and the camera rises.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function work(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared, sfx, mood } = ctx;

    // Opening sentence.
    const head = C.headline([K.opening[0], K.opening[1]], 'center xl');
    head.querySelectorAll('.hl-line')[1].innerHTML = 'is already <span class="soft">a job.</span>';
    place(head, hud, { x: 960, y: 530 });
    [...head.querySelectorAll('.hl-line')].forEach((ln, i) => {
      const a = inner(ln, { y: 130 });
      a.to(T.open + i * 0.5, 0.95, { y: 0 }, 'outExpo');
      a.to(T.verbs - 0.6 + i * 0.08, 0.55, { y: -140 }, 'inCubic');
      sfx(T.open + i * 0.5, 'word', { i });
    });

    // The desk: the camera tilts down onto it.
    cam.to(T.verbs - 0.5, 1.6, { x: 1210, y: 540, s: 1.06, rx: 24, ry: -8 }, 'inOutCubic');
    cam.to(T.verbs + 1.1, T.repeat - (T.verbs + 1.1), { ry: -6, s: 1.0, y: 560 }, 'inOutSine');
    sfx(T.verbs - 0.5, 'whoosh', { d: 1.6, gain: 0.5 });

    // The verb drum (screen space, its own perspective).
    const drum = h('div.drum');
    const drumA = place(drum, hud, { x: 120, y: 540, o: 1 }, { anchor: 'left' });
    const verbs = K.verbs.map((v) => {
      const el = h('div.verb', { text: v });
      drum.append(el);
      return inner(el, { rx: -90, o: 0 });
    });
    // Occurrences: each verb in turn, then "Repeat." spins the reel through the loop twice.
    const seq = K.verbs.map((_, i) => [i, T.verb(i), i < K.verbs.length - 1 ? T.verb(i + 1) : T.repeat + 0.5]);
    let t = T.repeat + 0.5;
    const spin = [0.16, 0.14, 0.12, 0.11, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.11, 0.12, 0.14]; // ends on Apply, then Repeat.
    spin.forEach((d, k) => {
      seq.push([k % 7, t, t + d]);
      t += d;
    });
    const last = [6, t, T.repeat + 2.6];
    seq.push(last);
    const byVerb = verbs.map(() => []);
    seq.forEach(([i, a, b]) => byVerb[i].push([a, b]));
    byVerb.forEach((occ, i) => {
      occ.sort((p, q) => p[0] - q[0]).forEach(([a, b], k) => {
        const fast = b - a < 0.3;
        const din = fast ? Math.min(0.09, (b - a) * 0.6) : 0.45;
        verbs[i].set(a - 0.001, { rx: -90, o: 0 });
        verbs[i].to(a, din, { rx: 0, o: 1 }, fast ? 'linear' : 'outCubic');
        verbs[i].to(b, fast ? din : 0.35, { rx: 90, o: 0 }, fast ? 'linear' : 'inCubic');
      });
    });
    seq.forEach(([i, a], k) => sfx(a, k < 7 ? 'verb' : 'reel', { i, k }));
    drumA.to(T.repeat + 2.3, 0.4, { o: 0 });

    // --- Objects fall onto the table: from above (z), tilted, landing with a settle.
    const drop = (a, t0, to, gain = 1) => {
      a.to(t0, 0.75, Object.assign({ z: 0, o: 1, rx: 0, ry: 0 }, to), 'outBack');
      sfx(t0 + 0.42, 'land', { gain });
    };

    // Find: three roles.
    const jobPos = [
      [1010, 236, -3],
      [1325, 222, 2],
      [1640, 244, -1.5],
    ];
    const jobs = K.firstJobs.map((job, i) => {
      const [x, y, r] = jobPos[i];
      const a = place(C.jobCard(job), world, { x: x + 40, y: y - 30, z: 520, r: r + 8, rx: -25, o: 0 }, null, job.id);
      drop(a, T.verb(0) + i * 0.14, { x, y, r }, 0.7);
      return a;
    });

    // Read: a long job description, its text scrolling on and on.
    const jd = C.jobDoc(K.jd);
    const jdA = place(jd, world, { x: 1040, y: 690, z: 600, r: 6, rx: -30, o: 0 }, null, 'jd');
    drop(jdA, T.verb(1), { y: 650, r: -2 });
    inner(jd.querySelector('.doc-scroll'), { y: 0 }).to(T.verb(1) + 0.4, 9, { y: -560 }, 'inOutSine');

    // Compare: the three roles lift in turn, square up, and settle side by side.
    jobs.forEach((a, i) => {
      const t0 = T.verb(2) + i * 0.16;
      a.to(t0, 0.3, { z: 60, r: 0 }, 'outCubic').to(t0 + 0.3, 0.45, { z: 0, y: 232 }, 'outBack');
      sfx(t0 + 0.55, 'tick', { gain: 0.6 });
    });

    // Adapt: one CV becomes three versions, fanned like a hand of cards.
    const cvPos = [
      [1330, 680, -8],
      [1400, 668, -1],
      [1470, 684, 7],
    ];
    const cvs = K.cvFiles.map((file, i) => {
      const id = i === 2 ? 'cv' : 'cv' + i;
      const a = place(C.cvDoc(file, 40 + i * 5), world, { x: 1400, y: 700, z: 480, r: 0, rx: -20, o: 0 }, null, id);
      drop(a, T.verb(3), { y: 668, r: -1 }, i === 2 ? 1 : 0);
      const [x, y, r] = cvPos[i];
      a.to(T.verb(3) + 0.8, 0.55, { x, y, r, z: i * 6 }, 'outBack');
      return a;
    });
    sfx(T.verb(3) + 0.85, 'fan');
    shared.cvs = cvs;

    // Write: a cover letter writes itself.
    const letter = C.letter(K.letter.greeting);
    const letterA = place(letter, world, { x: 1730, y: 640, z: 520, r: 8, rx: -25, o: 0 }, null, 'letter');
    drop(letterA, T.verb(4), { y: 616, r: 2.5 });
    [...letter.querySelectorAll('.ln')].forEach((ln, i) => {
      const t0 = T.verb(4) + 0.35 + i * 0.06;
      inner(ln, { sx: 0 }).to(t0, 0.25, { sx: 1 }, 'outCubic');
      if (i % 2 === 0) sfx(t0, 'type', { i });
    });

    // Apply: a form, a press, and two roles get "Applied".
    const form = C.form(K.form);
    const formA = place(form, world, { x: 1240, y: 930, z: 500, r: -6, rx: -25, o: 0 }, null, 'form');
    drop(formA, T.verb(5), { y: 905, r: -1.5, z: 12 });
    const btn = inner(form.querySelector('.btn'), { s: 1 });
    btn.to(T.verb(5) + 0.6, 0.1, { s: 0.9 }, 'outCubic').to(T.verb(5) + 0.7, 0.3, { s: 1 }, 'outBack');
    sfx(T.verb(5) + 0.6, 'click');
    shared.slots = [];
    [0, 2].forEach((j, k) => {
      const slot = jobs[j].el.querySelector('.status-slot');
      slot.textContent = 'Applied';
      shared.slots[j] = inner(slot, { o: 0, s: 0.6 }).to(T.verb(5) + 0.8 + k * 0.15, 0.4, { o: 1, s: 1 }, 'outBack');
      sfx(T.verb(5) + 0.8 + k * 0.15, 'ding', { k });
    });

    // Mood: the calm app stage starts cooling as the work piles up.
    mood.to(T.verbs, T.repeat - T.verbs, { tense: 0.45 }, 'inOutSine');

    // Repeat: the camera rises off the desk.
    cam.to(T.repeat, 2.6, { x: 1180, y: 600, s: 0.7, rx: 44, ry: 6 }, 'inOutCubic');
    sfx(T.repeat, 'whoosh', { d: 2.6, gain: 0.8 });

    shared.jobs = jobs;
    shared.coreItems = { jd: jdA, letter: letterA, form: formA };
  });
})(window.Applicable = window.Applicable || {});
