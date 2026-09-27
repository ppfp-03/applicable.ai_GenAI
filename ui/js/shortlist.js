/* Onboarding step 4: once the shortlist is built, its five cards can be browsed.
 *
 * Nothing here changes server state, so the row moves entirely in the browser:
 *  - drag the row (a quick flick moves one card);
 *  - scroll over it, sideways or with the wheel; at either end the page scrolls;
 *  - the arrows beside the slots, ← and → on the keyboard;
 *  - a click on a side card or on its slot brings it to the centre.
 * The row opens on the #1 role (views/onboarding.py step4). Each card sits its
 * neighbours' half-widths plus a gap away, at every position along the way, so
 * cards never overlap and none is ever drawn over another.
 * A rerun that draws the same shortlist keeps the card the user was on.
 */
(function () {
  if (window.__aaShort) return;
  window.__aaShort = 1;

  const W = 440;             // card width, stage px (ui/css/onboarding.css .cc)
  const GAP = 36;            // space between two neighbouring cards
  const SHRINK = .15;        // scale lost per card away from the centre
  const DUR = 450;           // ms, as Home's carousel
  const FLICK = .35;         // stage px per ms: a faster release moves one card
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Distance from the centre of a card `a` places out: the integral of the card
  // widths in between. For two neighbours it is their half-widths plus GAP.
  const offset = a => W * (a - SHRINK * a * a / 2) + GAP * a;
  const STEP = offset(1);    // centre to the next card

  const S = { p: 0, n: 0, key: '', raf: 0, drag: null, wheel: null, swallow: false };
  const row = () => document.querySelector('.cr-row[data-done]');
  const ratio = el => { const w = el.getBoundingClientRect().width; return w ? el.offsetWidth / w : 1; };
  const clamp = p => Math.max(0, Math.min(S.n - 1, p));

  // cubic-bezier(.2,.8,.2,1), the app's carousel easing.
  function ease(u) {
    const bx = t => .6 * t * (1 - t) * (1 - t) + .6 * t * t * (1 - t) + t * t * t;
    const by = t => 2.4 * t * (1 - t) * (1 - t) + 3 * t * t * (1 - t) + t * t * t;
    let lo = 0, hi = 1;
    for (let i = 0; i !== 24; i++) { const m = (lo + hi) / 2; if (bx(m) > u) hi = m; else lo = m; }
    return by((lo + hi) / 2);
  }

  /* Lay every card out for a continuous position p (p = index at the centre). */
  function place(p, transition) {
    const r = row(); if (!r) return;
    const at = Math.round(clamp(p));
    r.querySelectorAll('.cc').forEach(el => {
      const o = +el.dataset.i - p, a = Math.abs(o);
      const sc = Math.max(.4, 1 - SHRINK * a);
      const op = a <= 1 ? 1 - .45 * a : a <= 2 ? .55 - .3 * (a - 1) : Math.max(0, .25 * (3 - a));
      const f = Math.max(0, 1 - a);   // 1 at the centre: the glass thickens and lifts
      const st = el.style;
      st.transition = transition || 'none';
      st.transform = `translate(calc(-50% + ${(Math.sign(o) * offset(a)).toFixed(1)}px),-50%) scale(${sc.toFixed(4)})`;
      st.opacity = op.toFixed(3);
      st.zIndex = '2';
      st.pointerEvents = op < .05 ? 'none' : '';
      st.backgroundColor = `rgba(255,255,255,${(.8 + .15 * f).toFixed(3)})`;
      st.boxShadow = `0 1px 0 #fff inset,0 20px 50px rgba(28,40,64,${(.12 + .02 * f).toFixed(3)}),0 0 0 .5px rgba(0,0,0,.06)`;
      el.classList.toggle('c0', +el.dataset.i === at);
    });
    document.querySelectorAll('#cr-slots .slot').forEach(el => el.classList.toggle('cur', +el.dataset.i === at));
    const prev = document.querySelector('#cr-slots .cr-nav.prev'), next = document.querySelector('#cr-slots .cr-nav.next');
    if (prev) prev.classList.toggle('off', at === 0);
    if (next) next.classList.toggle('off', at === S.n - 1);
  }

  /* Glide from the current position to `to` on the app's curve. */
  function go(to) {
    to = clamp(Math.round(to));
    cancelAnimationFrame(S.raf);
    const from = S.p, t0 = performance.now();
    if (reduced || from === to) { S.p = to; place(to); return; }
    (function frame() {
      const u = Math.min(1, (performance.now() - t0) / DUR);
      S.p = from + (to - from) * ease(u);
      place(S.p);
      if (u !== 1) S.raf = requestAnimationFrame(frame);
    })();
  }

  /* Take over a freshly drawn row. The server's own classes already show the
   * same layout, so the hand-over is invisible; the first placement rides the
   * CSS transition that may still be sliding the row to the #1. */
  function sync() {
    const r = row();
    if (!r || r.dataset.aa) return;
    r.dataset.aa = '1';
    const cards = [...r.querySelectorAll('.cc')];
    const key = cards.map(c => c.querySelector('.cc-t') ? c.querySelector('.cc-t').textContent : '').join('|');
    S.n = cards.length;
    cancelAnimationFrame(S.raf);
    S.p = key === S.key ? clamp(Math.round(S.p)) : +r.dataset.cur || 0;
    S.key = key;
    place(S.p, 'transform .7s cubic-bezier(.2,.8,.2,1),opacity .7s,background-color .7s,box-shadow .7s');
  }
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; sync(); });
  }).observe(document.body, { childList: true, subtree: true });
  sync();

  // ───────────────────────── Input ─────────────────────────

  const stop = e => { e.preventDefault(); e.stopImmediatePropagation(); };

  window.addEventListener('click', e => {
    if (S.swallow) { stop(e); S.swallow = false; return; }
    if (!row()) return;
    const nav = e.target.closest('#cr-slots .cr-nav');
    if (nav) { stop(e); go(Math.round(S.p) + (nav.classList.contains('next') ? 1 : -1)); return; }
    const hit = e.target.closest('.cr-row[data-done] .cc, #cr-slots .slot');
    if (hit) { stop(e); go(+hit.dataset.i); }
  }, true);

  window.addEventListener('keydown', e => {
    if (!row() || e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    if (e.target.closest && e.target.closest('input,textarea,select,[contenteditable="true"]')) return;
    if (document.querySelector('.st-key-guide')) return;  // the intro sheet is up (ui/guide.py)
    stop(e);
    go(Math.round(S.p) + (e.key === 'ArrowRight' ? 1 : -1));
  }, true);

  /* Pointer velocity over the last ~100 ms, in window px per ms. */
  function velocity(pts) {
    const last = pts[pts.length - 1];
    const first = pts.find(p => last[0] - p[0] < 100) || last;
    return last[0] === first[0] ? 0 : (last[1] - first[1]) / (last[0] - first[0]);
  }
  const track = (pts, e) => { pts.push([e.timeStamp, e.clientX]); if (pts.length > 12) pts.shift(); };

  window.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    const r = e.target.closest('.cr-row[data-done]'); if (!r) return;
    cancelAnimationFrame(S.raf);
    S.drag = { x: e.clientX, y: e.clientY, p0: S.p, k: ratio(r), on: false, pts: [] };
    track(S.drag.pts, e);
  }, true);

  window.addEventListener('pointermove', e => {
    const d = S.drag; if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (!d.on) {
      if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { S.drag = null; go(S.p); return; }
      if (Math.abs(dx) < 6) return;
      d.on = true;
      document.documentElement.classList.add('aa-dragging');
    }
    track(d.pts, e);
    const raw = d.p0 - dx * d.k / STEP, c = clamp(raw);
    S.p = c + (raw - c) * .3;   // past either end the row gives, then springs back
    place(S.p);
  }, true);

  function release() {
    const d = S.drag; if (!d) return;
    S.drag = null;
    if (!d.on) { go(S.p); return; }
    document.documentElement.classList.remove('aa-dragging');
    S.swallow = true; setTimeout(() => { S.swallow = false; }, 80);
    const v = velocity(d.pts) * d.k;
    let to = Math.round(S.p);
    if (to === Math.round(d.p0) && Math.abs(v) > FLICK) to = Math.round(d.p0) - Math.sign(v);
    go(to);
  }
  window.addEventListener('pointerup', release, true);
  window.addEventListener('pointercancel', release, true);

  /* Scrolling follows the fingers (or the wheel) continuously, then settles on
   * the nearest card; a short scroll still moves one card. */
  window.addEventListener('wheel', e => {
    const r = e.target.closest && e.target.closest('.cr-row[data-done]'); if (!r || e.ctrlKey) return;
    const side = Math.abs(e.deltaX) > Math.abs(e.deltaY);
    let delta = side ? e.deltaX : e.deltaY;
    if (e.deltaMode === 1) delta *= 40; else if (e.deltaMode === 2) delta *= STEP;
    // The wheel at either end hands the scroll back to the page.
    if (!side && !S.wheel && ((delta < 0 && S.p <= 0) || (delta > 0 && S.p >= S.n - 1))) return;
    e.preventDefault();
    cancelAnimationFrame(S.raf);
    if (!S.wheel) S.wheel = { p0: Math.round(S.p), t: 0 };
    const raw = S.p + delta * ratio(r) / STEP, c = Math.max(-.2, Math.min(S.n - .8, raw));
    S.p = c;
    place(S.p);
    clearTimeout(S.wheel.t);
    S.wheel.t = setTimeout(() => {
      const w = S.wheel; S.wheel = null;
      let to = Math.round(S.p);
      if (to === w.p0 && Math.abs(S.p - w.p0) > .12) to = w.p0 + Math.sign(S.p - w.p0);
      go(to);
    }, 140);
  }, { capture: true, passive: false });
})();
