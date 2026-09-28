/*
 * Phase 1 — The normal application problem (≈0–12 s).
 * A calm sheet of paper. One sentence, then seven verbs; each verb puts its own object on
 * the desk, so the workload visibly accumulates. "Repeat." pulls the camera back.
 */
(function (A) {
  'use strict';

  (A.scenes = A.scenes || []).push(function work(ctx) {
    const { T, content: K, C, h, world, hud, place, inner, cam, shared } = ctx;

    // Opening sentence (screen space).
    const head = C.headline(K.opening, 'center xl');
    const headA = place(head, hud, { x: 960, y: 540, o: 1 });
    const lines = [...head.querySelectorAll('.hl-line')];
    lines.forEach((ln, i) => {
      const a = inner(ln, { y: 120, o: 1 });
      a.to(T.open + i * 0.55, 0.9, { y: 0 }, 'outExpo');
    });
    headA.to(T.verbs - 0.55, 0.6, { y: 470, o: 0, s: 0.96 }, 'inOutCubic');

    // Verbs, stacked on the left of the desk (world space: they shrink with it on "Repeat.").
    const verbs = K.verbs.map((v, i) => {
      const el = h('div.verb', null, h('div.hl-mask', null, h('div.hl-line', { text: v })));
      const a = place(el, world, { x: 150, y: 250 + i * 86, o: 1 }, { anchor: 'left' });
      const ln = inner(el.querySelector('.hl-line'), { y: 90 });
      ln.to(T.verb(i), 0.55, { y: 0 }, 'outExpo');
      if (i < K.verbs.length - 1) a.cls(T.verb(i + 1), 'is-past');
      return a;
    });
    shared.verbs = verbs;

    // --- Find: three roles arrive.
    const jobPos = [
      [1010, 250, -2.5],
      [1325, 232, 1.8],
      [1640, 256, -1.2],
    ];
    const jobs = K.firstJobs.map((job, i) => {
      const el = C.jobCard(job);
      const [x, y, r] = jobPos[i];
      const a = place(el, world, { x: x + 60, y: y + 30, r: r + 3, o: 0, s: 0.97 }, null, job.id);
      a.to(T.verb(0) + i * 0.14, 0.75, { x, y, r, o: 1, s: 1 }, 'outCubic');
      return a;
    });

    // --- Read: a long job description, its text scrolling on and on.
    const jd = C.jobDoc(K.jd);
    const jdA = place(jd, world, { x: 1045, y: 700, r: -2, o: 0 }, null, 'jd');
    jdA.to(T.verb(1), 0.8, { y: 640, o: 1 }, 'outCubic');
    const scroll = inner(jd.querySelector('.doc-scroll'), { y: 0 });
    scroll.to(T.verb(1) + 0.4, 9, { y: -520 }, 'inOutSine');

    // --- Compare: the three cards square up into a row; "vs" between them.
    jobs.forEach((a, i) => a.to(T.verb(2), 0.6, { y: 236, r: 0 }, 'inOutCubic'));
    [1167, 1482].forEach((x) => {
      const v = place(C.vs(), world, { x, y: 236, o: 0, s: 0.6 });
      v.to(T.verb(2) + 0.35, 0.4, { o: 1, s: 1 }, 'outBack').to(T.verb(4), 0.4, { o: 0, s: 0.8 });
    });

    // --- Adapt: one CV becomes three versions.
    const cvPos = [
      [1330, 660, -7],
      [1395, 650, -1],
      [1460, 664, 6],
    ];
    const cvs = K.cvFiles.map((file, i) => {
      const el = C.cvDoc(file, 40 + i * 5);
      const id = i === 2 ? 'cv' : 'cv' + i;
      const a = place(el, world, { x: 1395, y: 700, r: -1, o: 0 }, null, id);
      const [x, y, r] = cvPos[i];
      a.to(T.verb(3), 0.5, { y: 650, o: 1 }, 'outCubic').to(T.verb(3) + 0.5, 0.6, { x, y, r }, 'outBack');
      return a;
    });
    shared.cvs = cvs;

    // --- Write: a cover letter writes itself, line by line.
    const letter = C.letter(K.letter.greeting);
    const letterA = place(letter, world, { x: 1720, y: 660, r: 2.5, o: 0 }, null, 'letter');
    letterA.to(T.verb(4), 0.6, { y: 610, o: 1 }, 'outCubic');
    [...letter.querySelectorAll('.ln')].forEach((ln, i) => {
      inner(ln, { sx: 0 }).to(T.verb(4) + 0.3 + i * 0.075, 0.28, { sx: 1 }, 'outCubic');
    });

    // --- Apply: a form, a press, and "Applied" lands on two cards.
    const form = C.form(K.form);
    const formA = place(form, world, { x: 1215, y: 960, r: -1.5, o: 0 }, null, 'form');
    formA.to(T.verb(5), 0.6, { y: 905, o: 1 }, 'outCubic');
    const btn = inner(form.querySelector('.btn'), { s: 1 });
    btn.to(T.verb(5) + 0.55, 0.12, { s: 0.92 }, 'outCubic').to(T.verb(5) + 0.67, 0.25, { s: 1 }, 'outBack');
    [0, 2].forEach((j, k) => {
      const slot = jobs[j].el.querySelector('.status-slot');
      slot.textContent = 'Applied';
      inner(slot, { o: 0, s: 0.6 }).to(T.verb(5) + 0.75 + k * 0.15, 0.4, { o: 1, s: 1 }, 'outBack');
    });

    // --- Repeat: pull back; the desk turns out to be a small corner of the problem.
    cam.to(T.repeat, 2.2, { s: 0.62, x: 1080, y: 560 }, 'inOutCubic');
    verbs.forEach((a, i) => a.to(T.repeat + 1.6 + i * 0.05, 0.8, { o: 0 }, 'inOutSine'));

    shared.jobs = jobs;
    shared.coreItems = { jd: jdA, letter: letterA, form: formA };
  });
})(window.Applicable = window.Applicable || {});
