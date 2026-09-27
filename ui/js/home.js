/* Home motion: the carousel and the top matches strip move in the browser,
 * then commit through their native buttons.
 *
 * Every state change still goes through a real Streamlit widget: the script
 * animates first, then clicks the widget that makes the change. Clicks it
 * handles itself are stopped in the capture phase, before React sees them.
 */
(function () {
  if (window.__aaHome) { setTimeout(window.__aaHome.edges, 300); return; }

  const H = document.documentElement;
  const EASE = 'cubic-bezier(.2,.8,.2,1)';
  const STEP = 208;          // one top-match card plus its gap
  const SLIDE = 470;         // carousel: centre to side card, in stage px

  // Page zoom: pointer deltas are in window px, layout in stage px.
  const ratio = el => { const w = el.getBoundingClientRect().width; return w ? el.offsetWidth / w : 1; };
  const keyOf = el => { const m = / st-key-([\w-]+)/.exec(' ' + el.className); return m ? m[1] : ''; };

  let bypass = false, swallow = false;
  const press = btn => { bypass = true; try { btn.click(); } finally { bypass = false; } };
  const swallowClick = () => { swallow = true; setTimeout(() => { swallow = false; }, 80); };

  /* Run fn once cond() holds, checked every frame so it lands before paint. */
  function waitFor(cond, fn, ms) {
    const t0 = performance.now();
    (function loop() {
      if (cond() || performance.now() - t0 > ms) { fn(); return; }
      requestAnimationFrame(loop);
    })();
  }

  /* Pointer velocity over the last ~100 ms, in window px per ms. */
  function velocity(pts) {
    const last = pts[pts.length - 1];
    const first = pts.find(p => last[0] - p[0] < 100) || last;
    return last[0] === first[0] ? 0 : (last[1] - first[1]) / (last[0] - first[0]);
  }
  const track = (pts, e) => { pts.push([e.timeStamp, e.clientX]); if (pts.length > 12) pts.shift(); };

  // ───────────────────────── Carousel ─────────────────────────

  const CAR = { p: null, drag: null, token: 0 };
  const side = () => document.querySelector('.car-side');

  /* Lay every card out for a continuous position p (p = index at centre). */
  function place(p, animate) {
    const s = side(); if (!s) return;
    const n = +s.dataset.n;
    s.querySelectorAll('.uc').forEach(el => {
      let o = ((+el.dataset.j - p) % n + n) % n;
      if (o > n / 2) o -= n;
      const a = Math.abs(o), dir = Math.sign(o);
      let x, sc, op;
      if (a <= 1) { x = SLIDE * a; sc = 1 - .2 * a; op = 1 - .2 * a; }
      else if (a <= 2) { x = SLIDE + 250 * (a - 1); sc = .8 - .18 * (a - 1); op = .8 * (2 - a); }
      else { x = 720; sc = .62; op = 0; }
      // Towards the centre the glass thickens and lifts into the native card's
      // look, so the hand-over at either end of a move is invisible.
      const f = Math.max(0, 1 - a);
      const st = el.style;
      // z-index rides the same curve: the two cards swap layers halfway, not on the first frame.
      st.transition = animate ? ['transform', 'opacity', 'background-color', 'box-shadow', 'z-index'].map(k => `${k} .45s ${EASE}`).join(',') : 'none';
      st.transform = `translateX(calc(-50% + ${(dir * x).toFixed(1)}px)) scale(${sc.toFixed(4)})`;
      st.opacity = op.toFixed(3);
      st.zIndex = a < .5 ? 5 : a < 1.5 ? 4 : 3;
      st.backgroundColor = `rgba(255,255,255,${(.62 + .35 * f).toFixed(3)})`;
      st.boxShadow = `0 1px 0 #fff inset,0 ${(8 + 12 * f).toFixed(1)}px ${(28 + 22 * f).toFixed(1)}px rgba(28,40,64,${(.07 + .05 * f).toFixed(3)}),0 0 0 .5px rgba(0,0,0,${(.05 + .01 * f).toFixed(3)})`;
    });
  }

  /* Hand back to the native card in one frame: no cross-fade, so the glass
   * never thins out on the way. */
  function settle() {
    CAR.p = null;
    const cards = document.querySelectorAll('.car-side .uc');
    cards.forEach(el => { el.style.cssText = 'transition:none'; });
    H.classList.remove('aa-car-moving');
    dotsRest();
    void document.body.offsetWidth;
    requestAnimationFrame(() => cards.forEach(el => { el.style.cssText = ''; }));
  }

  /* Animate to position `to`, then commit the card that lands in the centre. */
  function slide(to) {
    const s = side(); if (!s) return;
    const n = +s.dataset.n;
    if (CAR.p === null) CAR.p = +s.dataset.cur;
    H.classList.add('aa-car-moving');
    place(CAR.p, false);
    void s.offsetWidth;
    CAR.p = to;
    place(to, true);
    dotsTween(to);
    const tok = ++CAR.token;
    const idx = ((Math.round(to) % n) + n) % n;
    setTimeout(() => { if (tok === CAR.token) commit(idx, tok); }, 460);
  }

  function commit(idx, tok) {
    const shown = () => document.querySelector(`.st-key-card-uc .ucx[data-i="${idx}"]`);
    if (shown()) { settle(); return; }
    const btn = document.querySelector(`.st-key-dot-${idx} button, .st-key-dot-on-${idx} button`);
    if (!btn) { settle(); return; }
    press(btn);
    waitFor(() => tok !== CAR.token || shown(), () => { if (tok === CAR.token) settle(); }, 6000);
  }

  const base = () => { const s = side(); return CAR.p === null ? +s.dataset.cur : Math.round(CAR.p); };

  function toIndex(idx) {
    const s = side(), n = +s.dataset.n, b = base();
    let d = ((idx - b) % n + n) % n;
    if (d > n / 2) d -= n;
    slide(b + d);
  }

  // ───────────────────────── Dots ─────────────────────────
  /* While the carousel moves, the dash is a liquid-glass lens that rides the
   * same continuous position: the dots swell and shrink as it passes, and the
   * lens stretches ahead with its speed and settles when it lands. At rest the
   * page's own dash (CSS) takes over; both look the same. */

  const DOT = { p: null, raf: 0, v: 0, dir: 0, s: 0, t: 0 };
  const DOT_W = 6, DOT_ON = 20;

  // cubic-bezier(.2,.8,.2,1), the carousel's easing, for the per-frame tween.
  function ease(u) {
    const bx = t => 3 * .2 * t * (1 - t) * (1 - t) + 3 * .2 * t * t * (1 - t) + t * t * t;
    const by = t => 3 * .8 * t * (1 - t) * (1 - t) + 3 * t * t * (1 - t) + t * t * t;
    let lo = 0, hi = 1;
    for (let i = 0; i !== 24; i++) { const m = (lo + hi) / 2; if (bx(m) > u) hi = m; else lo = m; }
    return by((lo + hi) / 2);
  }

  function dotParts() {
    const box = document.querySelector('.st-key-dots'); if (!box) return null;
    const btns = [];
    box.querySelectorAll('[class*="st-key-dot-"]').forEach(h => {
      const m = /^dot-(?:on-)?(\d+)$/.exec(keyOf(h)), b = h.querySelector('button');
      if (m && b) btns[+m[1]] = b;
    });
    if (!btns.length) return null;
    let lens = box.querySelector(':scope > .dot-lens');
    if (!lens) {
      lens = document.createElement('span');  // not a div: the row rules style its child divs
      lens.className = 'dot-lens';
      lens.append(document.createElement('i'), document.createElement('i'));
      box.appendChild(lens);
    }
    return { box, btns, lens };
  }

  /* Draw the dots for a continuous position p (index at the centre). */
  function dotsDraw(p) {
    const d = dotParts(); if (!d) return;
    const n = d.btns.length;
    const near = k => { let o = ((k - p) % n + n) % n; if (o > n / 2) o -= n; return Math.max(0, 1 - Math.abs(o)); };
    const w = d.btns.map((b, k) => DOT_W + (DOT_ON - DOT_W) * near(k));
    d.btns.forEach((b, k) => { b.style.transition = 'none'; b.style.width = w[k].toFixed(2) + 'px'; });
    // Slot edges in stage px, measured after the dots have swollen.
    const box = d.box.getBoundingClientRect(), k0 = ratio(d.box);
    const xs = d.btns.map(b => (b.getBoundingClientRect().left - box.left) * k0);
    const fl = Math.floor(p), t = p - fl, i = ((fl % n) + n) % n, j = (i + 1) % n;
    const [a, b] = d.lens.children;
    // Stretch leads in the direction of travel and squeezes the glass thin.
    const s = DOT.s, grow = 7 * s, dir = DOT.dir;
    const put = (el, left, right, op) => {
      if (dir > 0) right += grow; else if (dir) left -= grow;
      el.style.transform = `translateX(${left.toFixed(2)}px) scaleY(${(1 - .22 * s).toFixed(3)})`;
      el.style.width = Math.max(0, right - left).toFixed(2) + 'px';
      el.style.opacity = op.toFixed(3);
    };
    if (j === 0 && n > 1) {
      // Wrapping round: the dash drains out of the last dot into the first.
      put(a, xs[i], xs[i] + w[i], 1 - t);
      put(b, xs[j], xs[j] + w[j], t);
    } else {
      put(a, xs[i] + (xs[j] - xs[i]) * t, xs[i] + w[i] + (xs[j] + w[j] - xs[i] - w[i]) * t, 1);
      b.style.opacity = '0';
    }
    H.classList.add('aa-dots-live');
  }

  /* Follow p directly (dragging); speed sets the stretch. */
  function dotsTo(p) {
    cancelAnimationFrame(DOT.raf);
    const now = performance.now(), dt = Math.max(1, now - (DOT.t || now - 16));
    if (DOT.p !== null) DOT.v = (p - DOT.p) / dt;
    if (Math.abs(DOT.v) > 1e-4) DOT.dir = Math.sign(DOT.v);
    DOT.s += (Math.min(1, Math.abs(DOT.v) * 160) - DOT.s) * .35;
    DOT.p = p; DOT.t = now;
    dotsDraw(p);
  }

  /* Glide to `to` on the carousel's curve, then let the stretch relax. */
  function dotsTween(to) {
    const s = side(); if (!s) return;
    const from = DOT.p === null ? +s.dataset.cur : DOT.p, t0 = performance.now();
    if (DOT.p === null) { DOT.p = from; DOT.v = 0; DOT.s = 0; }
    cancelAnimationFrame(DOT.raf);
    (function frame() {
      const u = Math.min(1, (performance.now() - t0) / 450);
      const p = from + (to - from) * ease(u);
      dotsTo(p);
      if (u !== 1 || DOT.s > .01) DOT.raf = requestAnimationFrame(frame);
      else { DOT.s = 0; dotsDraw(p); }
    })();
  }

  function dotsRest() {
    cancelAnimationFrame(DOT.raf);
    DOT.p = null; DOT.v = 0; DOT.dir = 0; DOT.s = 0; DOT.t = 0;
    const d = dotParts();
    if (d) d.btns.forEach(b => { b.style.transition = ''; b.style.width = ''; });
    H.classList.remove('aa-dots-live');
  }

  // ───────────────────────── Top matches ─────────────────────────

  const MR = { drag: null };

  function edge(el) {
    const max = el.scrollWidth - el.clientWidth;
    el.dataset.s = max <= 1 ? 'none' : el.scrollLeft <= 1 ? 'start' : el.scrollLeft >= max - 1 ? 'end' : 'mid';
  }
  function edges() { document.querySelectorAll('.st-key-mr').forEach(edge); }

  function scrollToCard(el, left) {
    const max = el.scrollWidth - el.clientWidth;
    el.scrollTo({ left: Math.max(0, Math.min(max, left)), behavior: 'smooth' });
  }

  // ───────────────────────── Input ─────────────────────────

  window.addEventListener('click', e => {
    if (swallow) { e.preventDefault(); e.stopImmediatePropagation(); swallow = false; return; }
    if (bypass) return;
    const btn = e.target.closest('button'); if (!btn) return;
    const host = btn.closest('[class*="st-key-"]'); if (!host) return;
    const key = keyOf(host);
    let m;
    const stop = () => { e.preventDefault(); e.stopImmediatePropagation(); };

    if (side()) {
      if (key === 'ib-prev' || key === 'side-m1') { stop(); slide(base() - 1); return; }
      if (key === 'ib-next' || key === 'side-p1' || key === 'uc-later' || key === 'uc-q-later') { stop(); slide(base() + 1); return; }
      if ((m = /^dot-(?:on-)?(\d+)$/.exec(key))) { stop(); toIndex(+m[1]); return; }
    }
    if (key === 'ib-mprev' || key === 'ib-mnext') {
      const el = document.querySelector('.st-key-mr'); if (!el) return;
      stop();
      scrollToCard(el, (Math.round(el.scrollLeft / STEP) + (key === 'ib-mnext' ? 1 : -1)) * STEP);
      return;
    }
  }, true);

  window.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    const car = e.target.closest('.st-key-car');
    if (car && side()) {
      CAR.drag = { x: e.clientX, y: e.clientY, p0: CAR.p === null ? +side().dataset.cur : CAR.p, k: ratio(car), on: false, pts: [] };
      track(CAR.drag.pts, e);
      return;
    }
    const mr = e.target.closest('.st-key-mr');
    if (mr && e.pointerType === 'mouse') {
      MR.drag = { x: e.clientX, left: mr.scrollLeft, el: mr, k: ratio(mr), on: false, pts: [] };
      track(MR.drag.pts, e);
    }
  }, true);

  window.addEventListener('pointermove', e => {
    const c = CAR.drag;
    if (c) {
      const dx = e.clientX - c.x, dy = e.clientY - c.y;
      if (!c.on) {
        if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { CAR.drag = null; return; }
        if (Math.abs(dx) < 6) return;
        c.on = true; CAR.token++;
        H.classList.add('aa-car-moving', 'aa-dragging');
      }
      track(c.pts, e);
      CAR.p = c.p0 - dx * c.k / SLIDE;
      place(CAR.p, false);
      dotsTo(CAR.p);
      return;
    }
    const d = MR.drag;
    if (d) {
      const dx = e.clientX - d.x;
      if (!d.on) {
        if (Math.abs(dx) < 5) return;
        d.on = true;
        d.el.style.scrollSnapType = 'none';
        d.el.style.scrollBehavior = 'auto';
        H.classList.add('aa-dragging');
      }
      track(d.pts, e);
      d.el.scrollLeft = d.left - dx * d.k;
    }
  }, true);

  function release() {
    const c = CAR.drag;
    if (c) {
      CAR.drag = null;
      if (!c.on) return;
      H.classList.remove('aa-dragging');
      swallowClick();
      const v = velocity(c.pts) * c.k;                    // stage px per ms
      let to = Math.round(CAR.p);
      if (to === Math.round(c.p0) && Math.abs(v) > .35) to = Math.round(c.p0) - Math.sign(v);
      slide(to);
      return;
    }
    const d = MR.drag;
    if (d) {
      MR.drag = null;
      if (!d.on) return;
      H.classList.remove('aa-dragging');
      swallowClick();
      const v = velocity(d.pts) * d.k;
      d.el.style.scrollBehavior = '';
      scrollToCard(d.el, Math.round((d.el.scrollLeft - v * 220) / STEP) * STEP);
      setTimeout(() => { d.el.style.scrollSnapType = ''; }, 650);
    }
  }
  window.addEventListener('pointerup', release, true);
  window.addEventListener('pointercancel', release, true);

  window.addEventListener('scroll', e => {
    const el = e.target;
    if (el && el.classList && el.classList.contains('st-key-mr')) edge(el);
  }, true);

  window.__aaHome = { edges };
  setTimeout(edges, 300);
})();
