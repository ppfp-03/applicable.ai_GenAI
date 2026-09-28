/* Applications: drag a card to another lane to change its stage.
 *
 * The card follows the pointer in the browser; dropping it on another lane
 * presses that card's hidden "move" button (.st-key-mv-ROLE--STAGE), so
 * the change itself still goes through Streamlit and the store. A press
 * without movement stays an ordinary click that selects the card.
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
  const START = 6;  // px of movement before a press becomes a drag

  // Page zoom: pointer deltas are in window px, layout in stage px.
  const ratio = el => { const w = el.getBoundingClientRect().width; return w ? el.offsetWidth / w : 1; };
  const keyAfter = (el, prefix) => {
    const m = new RegExp(' st-key-' + prefix + '([\\w-]+)').exec(' ' + (el.className || ''));
    return m ? m[1] : null;
  };
  const lanes = () => document.querySelectorAll('[class*="st-key-gl-lane-"]');

  function laneAt(x, y) {
    const el = document.elementsFromPoint(x, y).find(n => keyAfter(n, 'gl-lane-'));
    return el ? { el, stage: keyAfter(el, 'gl-lane-') } : null;
  }

  function mark(target) {
    lanes().forEach(l => l.classList.toggle('ap-over', !!target && l === target.el));
  }

  // Each lane is glass (backdrop-filter), which makes it its own stacking
  // context: a card's z-index only counts inside its lane, so lanes painted
  // later would cover it. The lane it comes from is raised for the drag.
  function settle(d) {
    d.card.classList.remove('ap-lift');
    d.card.style.transform = '';
    d.card.style.transition = '';
    d.lane.classList.remove('ap-from');
  }

  let drag = null, swallow = false, bypass = false;
  // A press made by this script must reach Streamlit even while the click
  // that follows a drop is being swallowed.
  const press = btn => { bypass = true; try { btn.click(); } finally { bypass = false; } };

  window.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.pointerType === 'touch') return;
    const card = e.target.closest('[class*="st-key-hit-app-"]');
    const lane = card && card.closest('[class*="st-key-gl-lane-"]');
    if (!card || !lane) return;
    drag = { card, lane, role: keyAfter(card, 'hit-app-'), from: keyAfter(lane, 'gl-lane-'),
             x: e.clientX, y: e.clientY, k: ratio(card), on: false };
  }, true);

  window.addEventListener('pointermove', e => {
    const d = drag;
    if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (!d.on) {
      if (Math.hypot(dx, dy) < START) return;
      d.on = true;
      d.card.classList.add('ap-lift');
      d.lane.classList.add('ap-from');
      H.classList.add('aa-ap-drag');
    }
    e.preventDefault();
    d.card.style.transform = `translate(${dx * d.k}px, ${dy * d.k}px) rotate(1.5deg)`;
    const over = laneAt(e.clientX, e.clientY);
    mark(over && over.stage !== d.from ? over : null);
  }, true);

  function release(e) {
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
    if (btn) {
      settle(d);
      press(btn);
      return;
    }
    // Dropped where nothing changes: glide back.
    d.card.style.transition = 'transform .22s cubic-bezier(.2,.8,.2,1)';
    d.card.style.transform = '';
    setTimeout(() => settle(d), 230);
  }
  window.addEventListener('pointerup', release, true);
  window.addEventListener('pointercancel', release, true);

  window.addEventListener('click', e => {
    if (bypass || !swallow) return;
    swallow = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);
})();
