/* Applications: drag a card to another lane to change its stage.
 *
 * While dragging, a copy of the card (the ghost) follows the pointer in a
 * fixed layer above the page, and the card itself stays behind, faded, as a
 * placeholder. Dropping on another lane presses that card's hidden "move"
 * button (.st-key-mv-ROLE--STAGE), so the change itself still goes through
 * Streamlit and the store. The ghost glides into the new lane and waits there
 * until the rerun draws the real card, then lands on it and hands over: the
 * card never jumps back to its old lane or disappears between the two.
 * A press without movement stays an ordinary click that selects the card.
 *
 * Keep "less-than followed by a letter or slash" out of this file, comments
 * included: Streamlit sanitises st.html with DOMPurify, which drops a whole
 * script whose text looks like it contains a tag.
 *
 * Mouse and pen only: on touch the lanes keep scrolling as usual, and the
 * Stage menu in the side panel moves a card there.
 */
(function () {
  if (window.__aaApps) return;
  window.__aaApps = true;

  const H = document.documentElement;
  const START = 6;      // px of movement before a press becomes a drag
  const GLIDE = 220;    // ms for the ghost to settle into a slot
  const WAIT = 8000;    // ms to wait for the rerun before giving the move up
  const EASE = 'cubic-bezier(.2,.8,.2,1)';

  // Page zoom: pointer deltas and rects are in window px, layout in stage px.
  // The ghost layer carries the same zoom as the stage, so it is placed in
  // stage px as well.
  const ratio = el => { const w = el.getBoundingClientRect().width; return w ? el.offsetWidth / w : 1; };
  const keyAfter = (el, prefix) => {
    const m = new RegExp(' st-key-' + prefix + '([\\w-]+)').exec(' ' + (el.className || ''));
    return m ? m[1] : null;
  };
  const lanes = () => document.querySelectorAll('[class*="st-key-gl-lane-"]');
  const laneOf = stage => document.querySelector('.st-key-gl-lane-' + stage);
  const cardIn = (stage, role) => document.querySelector(`.st-key-gl-lane-${stage} .st-key-hit-app-${role}`);

  function laneAt(x, y) {
    const el = document.elementsFromPoint(x, y).find(n => keyAfter(n, 'gl-lane-'));
    return el ? { el, stage: keyAfter(el, 'gl-lane-') } : null;
  }

  function mark(target) {
    lanes().forEach(l => l.classList.toggle('ap-over', !!target && l === target.el));
  }

  // The ghost lives outside the lanes: each lane is glass (backdrop-filter),
  // its own stacking context, so a card moved inside one would slide under
  // the lanes painted after it. Its layer sits in the tab's container, where
  // this screen's (tab-scoped) rules reach it and the stage zoom applies.
  let layer = null;
  function ghostOf(tile) {
    if (!layer || !layer.isConnected) {
      layer = document.createElement('div');
      layer.className = 'aa-ap-layer';
      (tile.closest('[class*="st-key-tab-"]') || document.body).appendChild(layer);
    }
    const g = tile.cloneNode(true);
    g.classList.add('ap-ghost');
    g.style.width = tile.offsetWidth + 'px';
    layer.appendChild(g);
    return g;
  }

  function place(g, x, y, lifted, glide) {
    g.style.transition = glide ? `transform ${GLIDE}ms ${EASE}, box-shadow ${GLIDE}ms` : 'box-shadow .2s';
    g.style.transform = `translate(${x}px, ${y}px)` + (lifted ? ' rotate(1.5deg) scale(1.02)' : '');
    g.classList.toggle('ap-up', lifted);
  }

  // Where the ghost waits for the rerun: under the last card of the lane, or
  // under its header when the lane is empty. Window px.
  function slotIn(lane) {
    const cards = lane.querySelectorAll('[class*="st-key-hit-app-"]');
    const last = cards[cards.length - 1];
    const head = lane.querySelector('.lh');
    const above = ((last && last.querySelector('.ac')) || head || lane).getBoundingClientRect();
    const gap = parseFloat(getComputedStyle(lane).rowGap) || 8;
    return { x: above.left, y: above.bottom + gap / ratio(lane) };
  }

  // Classes only on Streamlit's nodes (no inline styles): a rerun may reuse
  // a node for another card, and resetting its class drops ours with it.
  function release(d) {
    if (d.card.isConnected) d.card.classList.remove('ap-src', 'ap-gone');
  }

  // The moved card's old copy stays in its old lane until the rerun ends
  // (Streamlit keeps it, faded, as a stale element) and React may reset its
  // classes meanwhile. A rule on its place keeps it hidden until it is gone.
  function bury(d) {
    const sel = `.st-key-gl-lane-${d.from} .st-key-hit-app-${d.role}`;
    const css = document.createElement('style');
    css.textContent = sel + '{opacity:0!important;transition:none!important}';
    document.head.appendChild(css);
    let obs = null;
    const lift = () => { if (obs) obs.disconnect(); clearTimeout(cap); css.remove(); };
    const cap = setTimeout(lift, WAIT + 2000);
    d.unbury = lift;
    return () => {
      if (!document.querySelector(sel)) { lift(); return; }
      obs = new MutationObserver(() => { if (!document.querySelector(sel)) lift(); });
      obs.observe(document.body, { childList: true, subtree: true });
    };
  }

  function finish(d, real) {
    d.g.remove();
    release(d);
    if (real) real.classList.remove('ap-hold');
  }

  // Waits for the rerun to draw the card in its new lane, then lands the
  // ghost on it and swaps them.
  function arrive(d, stage) {
    let over = false, obs = null;
    const stop = () => { over = true; if (obs) obs.disconnect(); clearTimeout(timer); };
    const check = () => {
      if (over) return;
      const real = cardIn(stage, d.role);
      const tile = real && real.querySelector('.ac');
      if (!tile || !tile.offsetWidth) return;
      stop();
      real.classList.add('ap-hold');
      // The card may read differently in its new stage (footer, selection):
      // land with what it will look like.
      d.g.className = tile.className + ' ap-ghost';
      d.g.innerHTML = tile.innerHTML;
      d.g.style.width = tile.offsetWidth + 'px';
      const r = tile.getBoundingClientRect();
      place(d.g, r.left * d.k, r.top * d.k, false, true);
      setTimeout(() => { finish(d, real); if (d.settle) d.settle(); }, GLIDE + 20);
    };
    const timer = setTimeout(() => {
      // No rerun came back: put the card back where it was.
      stop();
      home(d);
    }, WAIT);
    obs = new MutationObserver(check);
    obs.observe(document.body, { childList: true, subtree: true });
    check();
  }

  // Glide back to the card's own place (dropped where nothing changes).
  function home(d) {
    if (d.unbury) d.unbury();
    const r = d.tile.isConnected ? d.tile.getBoundingClientRect() : null;
    if (!r) { finish(d); return; }
    place(d.g, r.left * d.k, r.top * d.k, false, true);
    setTimeout(() => finish(d), GLIDE + 20);
  }

  let drag = null, swallow = false, bypass = false;
  // A press made by this script must reach Streamlit even while the click
  // that follows a drop is being swallowed.
  const press = btn => { bypass = true; try { btn.click(); } finally { bypass = false; } };

  window.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.pointerType === 'touch') return;
    const card = e.target.closest('[class*="st-key-hit-app-"]');
    const lane = card && card.closest('[class*="st-key-gl-lane-"]');
    const tile = card && card.querySelector('.ac');
    if (!card || !lane || !tile) return;
    drag = { card, lane, tile, role: keyAfter(card, 'hit-app-'), from: keyAfter(lane, 'gl-lane-'),
             x: e.clientX, y: e.clientY, k: ratio(card), on: false };
  }, true);

  window.addEventListener('pointermove', e => {
    const d = drag;
    if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (!d.on) {
      if (Math.hypot(dx, dy) < START) return;
      d.on = true;
      const r = d.tile.getBoundingClientRect();
      d.gx = r.left * d.k;
      d.gy = r.top * d.k;
      d.g = ghostOf(d.tile);
      d.card.classList.add('ap-src');
      H.classList.add('aa-ap-drag');
    }
    e.preventDefault();
    place(d.g, d.gx + dx * d.k, d.gy + dy * d.k, true, false);
    const over = laneAt(e.clientX, e.clientY);
    mark(over && over.stage !== d.from ? over : null);
  }, true);

  function drop(e) {
    const d = drag;
    drag = null;
    if (!d || !d.on) return;
    H.classList.remove('aa-ap-drag');
    mark(null);
    // The pointerup is followed by a click on the card: it must not select it.
    swallow = true;
    setTimeout(() => { swallow = false; }, 80);

    const over = e && e.type === 'pointerup' ? laneAt(e.clientX, e.clientY) : null;
    const btn = over && over.stage !== d.from
      ? document.querySelector(`.st-key-mv-${d.role}--${over.stage} button`)
      : null;
    if (!btn) { home(d); return; }

    // The card has left its lane; the ghost takes the free slot in the new
    // one while Streamlit runs the move.
    d.card.classList.add('ap-gone');
    d.settle = bury(d);
    const lane = laneOf(over.stage) || over.el;
    const s = slotIn(lane);
    place(d.g, s.x * d.k, s.y * d.k, false, true);
    arrive(d, over.stage);
    press(btn);
  }
  window.addEventListener('pointerup', drop, true);
  window.addEventListener('pointercancel', drop, true);

  window.addEventListener('click', e => {
    if (bypass || !swallow) return;
    swallow = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);
})();
