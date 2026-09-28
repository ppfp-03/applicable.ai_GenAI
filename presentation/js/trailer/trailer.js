/*
 * Trailer orchestration: builds the layers, runs every scene's choreography once (scenes only
 * *schedule* keyframes and sound cues; nothing animates at build time), then plays.
 *
 * Layers, back to front:
 *   bg        the app's stage: #F5F6F8 and four blurred glows (ui/shell.py), whose colour
 *             follows the story — cool while it's a problem, dusk abroad, warm once solved
 *   bloom     the warm light Applicable.ai brings in
 *   viewport  a perspective box; `world` inside it holds every persistent object in 3D and
 *             is moved by one virtual camera (position, zoom, tilt, orbit)
 *   hud       screen-space typography and the brand lockup
 */
(function (A) {
  'use strict';

  const { h, T } = A;

  const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  const mixRGB = (a, b, p) => a.map((v, i) => v + (b[i] - v) * p);
  const css = (rgb) => `rgb(${rgb.map((v) => Math.round(v)).join(',')})`;

  // The app's glows (ui/shell.py, colours through ui/palette.py) and three moods of them.
  //            bg         peach       lavender    mint        cream
  const MOODS = {
    calm: ['#F5F6F8', '#FCC9AF', '#F9D6C6', '#CDEBD8', '#FBDFBC'],
    tense: ['#EEEFF3', '#D6D2E8', '#E8CFC8', '#CBD6E6', '#E3DDD2'],
    night: ['#D9D9E3', '#B9B3D8', '#CDB2C2', '#AEBDD6', '#C7C0DC'],
    bloom: ['#F8F4F0', '#FDBE9E', '#FBCDB6', '#C2E9D1', '#FED7A8'],
  };
  const M = Object.fromEntries(Object.entries(MOODS).map(([k, v]) => [k, v.map(hex)]));
  // Glow geometry, from the app's 1600×1000 stage scaled to 1920×1080: [cx, cy, w, h, opacity]
  const GLOWS = [
    [228, 84, 1250, 950, 1],
    [1704, 300, 1150, 880, 1],
    [888, 1120, 1300, 860, 1],
    [1420, 1040, 960, 760, 0.8],
  ];

  function build(root) {
    root.innerHTML = '';
    const bg = h('div.layer.bg');
    const bloomLayer = h('div.layer');
    const viewport = h('div.layer.viewport');
    const world = h('div.world');
    viewport.append(world);
    const hud = h('div.layer.hud');
    const vignette = h('div.layer.vignette');
    const grain = h('div.layer.grain');
    root.append(bg, bloomLayer, viewport, vignette, hud, grain);

    const tl = new A.Timeline(T.end);
    const cues = { sfx: [] };

    // --- camera: an actor whose tracks drive the world transform.
    const cam = tl.add(h('div'), { x: 960, y: 540, s: 1, r: 0, rx: 0, ry: 0, z: 0, o: 1, blur: 0 });
    cam.render = () => {};
    let camCache = '', opCache = '', filterCache = '';
    tl.hook((t) => {
      const g = (p) => cam.at(p, t);
      const tf =
        `translate3d(960px,540px,${g('z').toFixed(1)}px) rotateX(${g('rx').toFixed(3)}deg) rotateY(${g('ry').toFixed(3)}deg) ` +
        `rotate(${g('r').toFixed(3)}deg) scale3d(${g('s').toFixed(5)},${g('s').toFixed(5)},${g('s').toFixed(5)}) ` +
        `translate3d(${(-g('x')).toFixed(2)}px,${(-g('y')).toFixed(2)}px,0)`;
      if (tf !== camCache) world.style.transform = camCache = tf;
      const o = g('o').toFixed(3);
      if (o !== opCache) viewport.style.opacity = opCache = o;
      const b = g('blur');
      const f = b > 0.05 ? `blur(${b.toFixed(1)}px)` : 'none';
      if (f !== filterCache) viewport.style.filter = filterCache = f;
    });

    /** Where a world point on the z = 0 plane lands on screen at time t (tilt ignored). */
    const toScreen = (px, py, t) => {
      const x = cam.at('x', t), y = cam.at('y', t), s = cam.at('s', t), r = (cam.at('r', t) * Math.PI) / 180;
      const dx = (px - x) * s, dy = (py - y) * s;
      return [960 + dx * Math.cos(r) - dy * Math.sin(r), 540 + dx * Math.sin(r) + dy * Math.cos(r)];
    };

    // --- background: glows as actors, colour from the mood weights.
    const mood = tl.add(h('div'), { tense: 0, night: 0, bloom: 0, vig: 0 });
    mood.render = () => {};
    const glows = GLOWS.map(([x, y, w, hh, o]) => {
      const el = h('div.glow', { style: { width: w + 'px', height: hh + 'px' } });
      return tl.add(bg.appendChild(el) && el, { x, y, o }, { anchor: 'center' });
    });
    glows.forEach((g) => g.el.classList.add('actor'));
    let bgCache = '';
    const glowCache = glows.map(() => '');
    tl.hook((t) => {
      const wT = mood.at('tense', t), wN = mood.at('night', t), wB = mood.at('bloom', t);
      const pick = (i) => {
        let c = M.calm[i];
        c = mixRGB(c, M.tense[i], wT);
        c = mixRGB(c, M.night[i], wN);
        c = mixRGB(c, M.bloom[i], wB);
        return css(c);
      };
      const b0 = pick(0);
      if (b0 !== bgCache) bg.style.backgroundColor = bgCache = b0;
      glows.forEach((g, i) => {
        const c = pick(i + 1);
        if (c !== glowCache[i]) g.el.style.setProperty('--c', (glowCache[i] = c));
      });
      vignette.style.opacity = mood.at('vig', t).toFixed(3);
    });

    const ctx = {
      tl, cam, world, hud, bg, bloomLayer, root, toScreen, mood, glows, GLOWS,
      T: A.T, content: A.content, C: A.C, h,
      /** Append `el` to `parent` and give it an actor. */
      place(el, parent, init, opts, id) {
        el.classList.add('actor');
        parent.append(el);
        return tl.add(el, init, opts, id);
      },
      /** An actor for an element that is already inside a placed element. */
      inner(el, init, opts, id) {
        el.classList.add('inflow');
        return tl.add(el, init, Object.assign({ anchor: 'none' }, opts), id);
      },
      /** Register a sound cue at time t (read by tools/export-cues.mjs → the synthesizer). */
      sfx(t, name, opts = {}) {
        cues.sfx.push(Object.assign({ t: Math.round(t * 1000) / 1000, name }, opts));
      },
      shared: {},
    };

    for (const scene of A.scenes) scene(ctx);
    // Positions that depend on laid-out text (rows inside panels) are measured now.
    for (const a of tl.actors) if (a.lazyY) a.track('y').keys[0].v = a.lazyY();
    cues.sfx.sort((a, b) => a.t - b.t);
    A.cues = { bpm: T.BPM, duration: T.end, marks: Object.fromEntries(Object.entries(T).filter(([, v]) => typeof v === 'number')), sfx: cues.sfx };
    return { tl, ctx };
  }

  A.buildTrailer = build;
})(window.Applicable = window.Applicable || {});
