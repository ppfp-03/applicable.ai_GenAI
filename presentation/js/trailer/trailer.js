/*
 * Trailer orchestration: builds the layers, runs every scene's choreography once (scenes
 * only *schedule* keyframes; nothing animates at build time), then plays the timeline.
 *
 * Layers, back to front:
 *   bg     solid colour, animated paper → dusk
 *   light  the paper "daylight" that Applicable.ai brings back
 *   world  every persistent object, seen through one virtual camera
 *   hud    screen-space typography and the brand lockup
 */
(function (A) {
  'use strict';

  const { h, T } = A;

  const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  const mix = (a, b, p) => {
    const x = hex(a), y = hex(b);
    return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * p)).join(',')})`;
  };

  function build(root) {
    root.innerHTML = '';
    const bg = h('div.layer.bg');
    const light = h('div.layer.light-layer');
    const viewport = h('div.layer.viewport');
    const world = h('div.world');
    viewport.append(world);
    const hud = h('div.layer.hud');
    root.append(bg, light, viewport, hud);

    const tl = new A.Timeline(T.end);

    // The camera is an actor whose element is never displayed: its tracks are read by a hook
    // that places the world so that (x, y) sits at the centre of the frame.
    const cam = tl.add(h('div'), { x: 960, y: 540, s: 1, r: 0, o: 1, blur: 0 });
    cam.render = () => {};
    let camCache = '', opCache = '', filterCache = '';
    tl.hook((t) => {
      const x = cam.at('x', t), y = cam.at('y', t), s = cam.at('s', t), r = cam.at('r', t);
      const tf = `translate3d(960px,540px,0) rotate(${r.toFixed(3)}deg) scale(${s.toFixed(5)}) translate3d(${(-x).toFixed(2)}px,${(-y).toFixed(2)}px,0)`;
      if (tf !== camCache) world.style.transform = camCache = tf;
      const o = cam.at('o', t).toFixed(3);
      if (o !== opCache) viewport.style.opacity = opCache = o;
      const b = cam.at('blur', t);
      const f = b > 0.05 ? `blur(${b.toFixed(1)}px)` : 'none';
      if (f !== filterCache) viewport.style.filter = filterCache = f;
    });

    /** Where a world point lands on screen at time t (for handing objects between layers). */
    const toScreen = (px, py, t) => {
      const x = cam.at('x', t), y = cam.at('y', t), s = cam.at('s', t), r = (cam.at('r', t) * Math.PI) / 180;
      const dx = (px - x) * s, dy = (py - y) * s;
      return [960 + dx * Math.cos(r) - dy * Math.sin(r), 540 + dx * Math.sin(r) + dy * Math.cos(r)];
    };

    // Background: paper, a slightly greyer paper at the freeze, dusk for the international act.
    const PAPER = '#FBF7F2', FROZEN = '#EFE8DD', DUSK = '#1B1814';
    tl.hook((t) => {
      let c;
      if (t < T.freeze) c = PAPER;
      else if (t < T.dusk) c = mix(PAPER, FROZEN, A.prog(t, T.freeze, T.freeze + 0.6, 'outCubic'));
      else c = mix(FROZEN, DUSK, A.prog(t, T.dusk, T.dusk + 1.2, 'inOutCubic'));
      bg.style.backgroundColor = c;
    });

    const ctx = {
      tl, cam, world, hud, bg, light, root, toScreen,
      T: A.T, content: A.content, C: A.C, h,
      /** Append `el` to `parent` and give it an actor. */
      place(el, parent, init, opts, id) {
        el.classList.add('actor');
        if (opts && opts.anchor === 'none') el.classList.add('inflow');
        parent.append(el);
        return tl.add(el, init, opts, id);
      },
      /** An actor for an element that is already inside a placed element. */
      inner(el, init, opts, id) {
        el.classList.add('inflow');
        return tl.add(el, init, Object.assign({ anchor: 'none' }, opts), id);
      },
      shared: {},
    };

    for (const scene of A.scenes) scene(ctx);
    return { tl, ctx };
  }

  A.buildTrailer = build;
})(window.Applicable = window.Applicable || {});
