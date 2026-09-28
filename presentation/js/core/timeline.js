/*
 * Deterministic timeline.
 *
 * Every visual property is a pure function of the playhead time t (seconds). Nothing
 * integrates frame deltas, so any frame can be rendered directly: seek, scrub, replay and
 * frame-by-frame capture all produce the identical picture.
 *
 *   Track  — piecewise keyframes for one numeric property.
 *   Actor  — one DOM element with transform/opacity/filter/clip tracks, step tracks
 *            (classes, text) and a small builder API used by the scenes.
 *   Timeline — owns actors and per-frame hooks; render(t) draws the frame at t.
 */
(function (A) {
  'use strict';

  const { ease } = A;

  class Track {
    constructor(initial) {
      this.keys = [{ t: -Infinity, v: initial, e: null }];
    }
    get last() {
      return this.keys[this.keys.length - 1];
    }
    /** Animate from the value held at t0 to v, over [t0, t1]. */
    to(t0, t1, v, curve) {
      const last = this.last;
      if (t0 < last.t - 1e-6) {
        throw new Error(`Track keys out of order: ${t0} < ${last.t}`);
      }
      if (t0 > last.t) this.keys.push({ t: t0, v: last.v, e: ease.linear });
      this.keys.push({ t: Math.max(t1, t0 + 1e-4), v, e: ease[curve || 'inOutCubic'] || curve });
      return this;
    }
    /** Jump to v at time t (no interpolation). */
    jump(t, v) {
      const last = this.last;
      if (t < last.t - 1e-6) throw new Error(`Track keys out of order: ${t} < ${last.t}`);
      this.keys.push({ t, v: last.v, e: ease.linear });
      this.keys.push({ t: t + 1e-4, v, e: ease.linear });
      return this;
    }
    at(t) {
      const k = this.keys;
      if (t <= k[0].t) return k[0].v;
      // Keys are few per track; a reverse scan from the end is fast enough and branch-simple.
      let i = k.length - 1;
      if (t >= k[i].t) return k[i].v;
      while (i > 0 && k[i - 1].t > t) i--;
      const a = k[i - 1];
      const b = k[i];
      if (a.t === -Infinity) return a.v; // before the first scheduled change
      const p = (t - a.t) / (b.t - a.t);
      return a.v + (b.v - a.v) * b.e(p);
    }
    /** Value the track will hold once everything scheduled so far has played. */
    get final() {
      return this.last.v;
    }
  }

  class StepTrack {
    constructor(initial) {
      this.keys = [{ t: -Infinity, v: initial }];
    }
    set(t, v) {
      this.keys.push({ t, v });
      this.keys.sort((a, b) => a.t - b.t);
      return this;
    }
    at(t) {
      let v = this.keys[0].v;
      for (let i = 1; i < this.keys.length; i++) {
        if (this.keys[i].t <= t) v = this.keys[i].v;
        else break;
      }
      return v;
    }
  }

  const DEFAULTS = {
    x: 0, y: 0, z: 0, s: 1, sx: 1, sy: 1, r: 0, rx: 0, ry: 0, o: 1, blur: 0,
    // Clip insets in %, for masks and reveals.
    ct: 0, cr: 0, cb: 0, cl: 0,
    // Generic numeric channels for hooks (counters, progress bars…).
    n: 0, w: 0,
  };

  const round = (v, p) => Math.round(v * p) / p;

  // Which point of the element sits at (x, y). 'none' leaves the element where layout put it.
  const ANCHORS = { center: ' translate(-50%,-50%)', left: ' translate(0,-50%)', none: '' };

  class Actor {
    /**
     * @param {HTMLElement} el
     * @param {object} init initial values, e.g. {x, y, o}
     * @param {object} [opts] {anchor: 'center'|'topleft', clip: bool}
     */
    constructor(el, init, opts) {
      init = init || {};
      opts = opts || {};
      this.el = el;
      this.tracks = {};
      this.steps = {};
      this.opts = opts;
      this.anchor = opts.anchor || 'center';
      this.cache = {};
      for (const k of Object.keys(init)) this.track(k).keys[0].v = init[k];
    }
    track(prop) {
      if (!this.tracks[prop]) this.tracks[prop] = new Track(DEFAULTS[prop] ?? 0);
      return this.tracks[prop];
    }
    /** Current scheduled end value of a property. */
    v(prop) {
      return this.tracks[prop] ? this.tracks[prop].final : DEFAULTS[prop] ?? 0;
    }
    /** Animate several properties over [t, t + d]. */
    to(t, d, props, curve) {
      for (const k of Object.keys(props)) this.track(k).to(t, t + d, props[k], curve);
      return this;
    }
    /** Set several properties instantly at t. */
    set(t, props) {
      for (const k of Object.keys(props)) this.track(k).jump(t, props[k]);
      return this;
    }
    /** Toggle a class from time t onward. */
    cls(t, name, on = true) {
      const key = 'class:' + name;
      if (!this.steps[key]) this.steps[key] = new StepTrack(false);
      this.steps[key].set(t, on);
      return this;
    }
    /** Replace textContent of `el` (defaults to the actor) from time t onward. */
    text(t, value, el) {
      const target = el || this.el;
      const key = 'text:' + (target.dataset.tid || (target.dataset.tid = Math.random().toString(36).slice(2)));
      if (!this.steps[key]) {
        this.steps[key] = new StepTrack(target.textContent);
        this.steps[key].el = target;
      }
      this.steps[key].set(t, value);
      return this;
    }
    has(prop) {
      return !!this.tracks[prop];
    }
    at(prop, t) {
      return this.tracks[prop] ? this.tracks[prop].at(t) : DEFAULTS[prop] ?? 0;
    }
    render(t) {
      const g = (p) => (this.tracks[p] ? this.tracks[p].at(t) : DEFAULTS[p]);
      const o = g('o');
      const style = this.el.style;
      const c = this.cache;

      const vis = o > 0.001 ? '' : 'hidden';
      if (c.vis !== vis) style.visibility = c.vis = vis;
      if (vis) return; // invisible: skip the rest of the work

      const x = g('x'), y = g('y'), z = g('z'), s = g('s'), sx = g('sx'), sy = g('sy');
      const r = g('r'), rx = g('rx'), ry = g('ry');
      const anchor = ANCHORS[this.anchor] || '';
      const tf =
        `translate3d(${round(x, 100)}px,${round(y, 100)}px,${round(z, 100)}px)${anchor}` +
        (rx ? ` rotateX(${round(rx, 1000)}deg)` : '') +
        (ry ? ` rotateY(${round(ry, 1000)}deg)` : '') +
        (r ? ` rotate(${round(r, 1000)}deg)` : '') +
        (s !== 1 || sx !== 1 || sy !== 1 ? ` scale(${round(s * sx, 10000)},${round(s * sy, 10000)})` : '');
      if (c.tf !== tf) style.transform = c.tf = tf;

      const op = String(round(o, 1000));
      if (c.o !== op) style.opacity = c.o = op;

      if (this.tracks.blur) {
        const b = g('blur');
        const f = b > 0.05 ? `blur(${round(b, 10)}px)` : 'none';
        if (c.f !== f) style.filter = c.f = f;
      }
      if (this.opts.clip) {
        const cp = `inset(${round(g('ct'), 100)}% ${round(g('cr'), 100)}% ${round(g('cb'), 100)}% ${round(g('cl'), 100)}% round ${this.opts.radius || 0}px)`;
        if (c.cp !== cp) style.clipPath = c.cp = cp;
      }
      for (const key in this.steps) {
        const st = this.steps[key];
        const v = st.at(t);
        if (c[key] === v) continue;
        c[key] = v;
        if (key.startsWith('class:')) this.el.classList.toggle(key.slice(6), !!v);
        else st.el.textContent = v;
      }
    }
  }

  class Timeline {
    constructor(duration) {
      this.duration = duration;
      this.actors = [];
      this.hooks = [];
      this.byId = Object.create(null);
    }
    /** Register an actor; `id` makes it reachable by later scenes. */
    add(el, init, opts, id) {
      const a = new Actor(el, init, opts);
      this.actors.push(a);
      if (id) {
        if (this.byId[id]) throw new Error('Duplicate actor id ' + id);
        this.byId[id] = a;
      }
      return a;
    }
    get(id) {
      const a = this.byId[id];
      if (!a) throw new Error('Unknown actor ' + id);
      return a;
    }
    /** A per-frame function of t, for things that are not transforms (colours, counters). */
    hook(fn) {
      this.hooks.push(fn);
    }
    render(t) {
      for (let i = 0; i < this.actors.length; i++) this.actors[i].render(t);
      for (let i = 0; i < this.hooks.length; i++) this.hooks[i](t);
    }
  }

  A.Track = Track;
  A.Actor = Actor;
  A.Timeline = Timeline;
})(window.Applicable = window.Applicable || {});
