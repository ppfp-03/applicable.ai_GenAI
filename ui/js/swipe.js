/* Onboarding Explore step: the story card can be dragged, thrown or keyed away.
 *
 * Every verdict still goes through its native button (views/onboarding.py):
 * the script throws the card out first, then clicks the button that records
 * the verdict. Clicks and keys it handles itself are stopped in the capture
 * phase, before React sees them.
 *
 *  - Drag right: I'd enjoy this. Drag left: Not for me. Drag up: Not sure.
 *    Released short of the threshold, the card springs back.
 *  - ← ↑ → and the three buttons below the card throw it the same way.
 *  - After the rerun React may reuse the card's node, so the classes and
 *    styles set here are cleared once the next story has been drawn.
 */
(function () {
  if (window.__aaSwipe) return;
  window.__aaSwipe = 1;

  const THROW = 120;       // stage px sideways past which a release commits
  const THROW_UP = 100;    // stage px upwards past which a release commits
  const FLICK = 0.6;       // stage px per ms: a faster release commits too…
  const FLICK_MIN = 0.5;   // …once it has covered this share of the threshold
  const STAMP = { r: 'I’D ENJOY THIS', l: 'NOT FOR ME', u: 'NOT SURE' };
  const KEYS = { ArrowRight: 'r', ArrowLeft: 'l', ArrowUp: 'u' };

  // Page zoom: pointer deltas are in window px, layout in stage px.
  const ratio = el => { const w = el.getBoundingClientRect().width; return w ? el.offsetWidth / w : 1; };
  const card = () => document.querySelector('.sw-card:not(.sw-done)');
  const button = d => document.querySelector(`.st-key-oo-sw${d} button`);
  const counter = () => { const b = document.querySelector('.sw-cnt b'); return b ? b.textContent : ''; };

  let busy = false, bypass = false, swallow = false, drag = null;

  function stamp(c, d, alpha) {
    const s = c.querySelector('.stamp'); if (!s) return;
    if (d) { s.textContent = STAMP[d]; s.dataset.d = d; }
    s.style.opacity = alpha;
  }

  function reset(c) {
    c.classList.remove('out-r', 'out-l', 'out-u', 'dragging');
    c.style.transition = 'none'; c.style.transform = ''; c.style.opacity = '';
    stamp(c, '', 0);
    void c.offsetWidth;
    c.style.transition = '';
  }

  /* Run fn once cond() holds, checked every frame, or after ms regardless. */
  function waitFor(cond, fn, ms) {
    const t0 = performance.now();
    (function loop() {
      if (cond() || performance.now() - t0 > ms) { fn(); return; }
      requestAnimationFrame(loop);
    })();
  }

  /* Throw the top card towards d, then record the verdict. */
  function throwOut(d) {
    const c = card(), b = button(d);
    if (!c || !b || busy) return;
    busy = true;
    const before = counter();
    stamp(c, d, 1);
    c.classList.remove('dragging');
    c.style.transition = '';
    c.classList.add('out-' + d);
    setTimeout(() => {
      bypass = true;
      try { b.click(); } finally { bypass = false; }
      waitFor(() => counter() !== before, () => {
        const n = card() || document.querySelector('.sw-card');
        if (n) {
          reset(n);
          n.classList.add('in');
          n.addEventListener('animationend', () => n.classList.remove('in'), { once: true });
        }
        busy = false;
      }, 4000);
    }, 300);
  }

  function springBack(c) {
    c.classList.remove('dragging');
    c.style.transition = '';
    c.style.transform = '';
    stamp(c, '', 0);
  }

  // ───────────────────────── Dragging ─────────────────────────

  document.addEventListener('pointerdown', e => {
    if (busy || e.button !== 0) return;
    const c = e.target.closest('.sw-card');
    if (!c || c.classList.contains('sw-done')) return;
    drag = { c, id: e.pointerId, x: e.clientX, y: e.clientY, k: ratio(c), pts: [[e.timeStamp, 0, 0]], moved: false };
    c.setPointerCapture(e.pointerId);
  }, true);

  document.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const dx = (e.clientX - drag.x) * drag.k, dy = (e.clientY - drag.y) * drag.k;
    if (!drag.moved && Math.hypot(dx, dy) < 4) return;
    drag.moved = true;
    drag.pts.push([e.timeStamp, dx, dy]); if (drag.pts.length > 12) drag.pts.shift();
    const c = drag.c;
    c.classList.add('dragging');
    c.style.transition = 'none';
    c.style.transform = `translate(${dx.toFixed(1)}px,${dy.toFixed(1)}px) rotate(${(dx / 22).toFixed(2)}deg)`;
    const up = -dy > Math.abs(dx);
    const d = up ? 'u' : dx > 0 ? 'r' : 'l';
    stamp(c, d, Math.min(1, (up ? -dy / THROW_UP : Math.abs(dx) / THROW)));
  }, true);

  function release(e) {
    if (!drag || e.pointerId !== drag.id) return;
    const { c, pts, moved } = drag;
    drag = null;
    if (!moved) return;
    swallow = true; setTimeout(() => { swallow = false; }, 80);
    const last = pts[pts.length - 1];
    const first = pts.find(p => last[0] - p[0] < 100) || last;
    const dt = Math.max(1, last[0] - first[0]);
    const vx = (last[1] - first[1]) / dt, vy = (last[2] - first[2]) / dt;
    const [, dx, dy] = last;
    const up = -dy > Math.abs(dx);
    const flickUp = -vy > FLICK && -dy > THROW_UP * FLICK_MIN;
    const flickSide = Math.abs(vx) > FLICK && Math.abs(dx) > THROW * FLICK_MIN && Math.sign(vx) === Math.sign(dx);
    if (up && (-dy > THROW_UP || flickUp)) throwOut('u');
    else if (!up && (Math.abs(dx) > THROW || flickSide)) throwOut(dx > 0 ? 'r' : 'l');
    else springBack(c);
  }
  document.addEventListener('pointerup', release, true);
  document.addEventListener('pointercancel', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const c = drag.c; drag = null; springBack(c);
  }, true);

  // ───────────────────────── Buttons and keys ─────────────────────────

  document.addEventListener('click', e => {
    if (bypass) return;
    if (swallow) { e.stopPropagation(); e.preventDefault(); return; }
    const wrap = e.target.closest('[class*="st-key-oo-sw"]');
    if (!wrap || !card()) return;
    const m = / st-key-oo-sw([lur])\b/.exec(' ' + wrap.className);
    if (!m) return;
    e.stopPropagation(); e.preventDefault();
    throwOut(m[1]);
  }, true);

  window.addEventListener('keydown', e => {
    const d = KEYS[e.key];
    if (!d || e.altKey || e.ctrlKey || e.metaKey || !card()) return;
    if (e.target.closest && e.target.closest('input,textarea,[contenteditable="true"]')) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (!e.repeat) throwOut(d);
  }, true);
})();
