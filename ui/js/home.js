/* Home motion: the carousel, the top matches strip and the wallet move in the
 * browser, then commit through their native buttons.
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
      const st = el.style;
      st.transition = animate ? `transform .45s ${EASE},opacity .45s ${EASE},background-color .45s ${EASE}` : 'none';
      st.transform = `translateX(calc(-50% + ${(dir * x).toFixed(1)}px)) scale(${sc.toFixed(4)})`;
      st.opacity = op.toFixed(3);
      st.zIndex = a < .5 ? 5 : a < 1.5 ? 4 : 3;
      st.backgroundColor = `rgba(255,255,255,${(.62 + .35 * Math.max(0, 1 - a)).toFixed(3)})`;
    });
  }

  function settle() {
    CAR.p = null;
    document.querySelectorAll('.car-side .uc').forEach(el => { el.style.cssText = ''; });
    H.classList.remove('aa-car-moving');
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

  // ───────────────────────── Wallet ─────────────────────────

  const SCALE = p => [.9, .94, .97][p] ?? 1;

  function restack() {
    document.querySelectorAll('.wback .wc').forEach(c => {
      const p = +c.dataset.p, st = c.style;
      st.transition = 'none';
      st.top = p * 28 + 'px'; st.transform = `scale(${SCALE(p)})`; st.zIndex = p + 1; st.height = '';
      void c.offsetWidth;
      st.transition = '';
    });
    H.classList.remove('aa-wal-lift');
  }

  /* The picked card rises into the front slot, the ones behind it close up. */
  function pick(pos, btn) {
    const wc = document.querySelector(`.wback .wc[data-p="${pos}"]`);
    const front = document.querySelector('.st-key-wfront');
    if (!wc || !front || H.classList.contains('aa-wal-lift')) { press(btn); return; }
    const k = wc.dataset.k;
    document.querySelectorAll('.wback .wc').forEach(c => {
      const p = +c.dataset.p;
      if (p > pos) { c.style.top = (p - 1) * 28 + 'px'; c.style.transform = `scale(${SCALE(p - 1)})`; }
    });
    wc.style.zIndex = 6;
    wc.style.top = front.offsetTop + 'px';
    wc.style.height = front.offsetHeight + 'px';
    wc.style.transform = 'scale(1)';
    H.classList.add('aa-wal-lift');
    setTimeout(() => {
      press(btn);
      waitFor(() => document.querySelector(`.st-key-wfront .wf[data-k="${k}"]`), restack, 6000);
    }, 380);
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
    if ((m = /^wpick-(\d+)$/.exec(key))) { stop(); pick(+m[1], btn); }
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
