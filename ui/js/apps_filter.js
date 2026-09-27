/* Home's Applications card: a liquid-glass lens under the lit stage chip.
 *
 * One lens element, made here and kept across reruns, sits behind the chips.
 * On a click it glides to the chosen chip at once (stretching as it moves, the
 * way Apple's liquid glass does), then the rerun confirms it through the
 * marker the page renders (.af-mark data-cur / data-ring). The choice itself
 * is still the chip's own Streamlit button.
 *
 * Keep "less-than followed by a letter or slash" out of this file, comments
 * included: Streamlit sanitises st.html with DOMPurify, which drops a whole
 * script whose text looks like it contains a tag.
 */
(function () {
  if (window.__aaAppsFilter) { window.__aaAppsFilter.sync(false); return; }

  const EASE = 'cubic-bezier(.3,1.35,.5,1)';   // a little overshoot, like glass settling
  const MS = 520;

  const row = () => document.querySelector('.st-key-gl-apps .st-key-af');
  const chipOf = (af, stage) => af && af.querySelector('.st-key-af-' + stage);
  const stageOf = el => { const m = / st-key-af-(\w+)/.exec(' ' + (el.className || '')); return m ? m[1] : null; };

  function lensIn(af) {
    let lens = af.querySelector(':scope > .af-lens');
    if (!lens) {
      lens = document.createElement('span');  // not a div: the chips' row rules style every child div
      lens.className = 'af-lens';
      lens.appendChild(document.createElement('i'));
      af.prepend(lens);
      af.classList.add('has-lens');
      lens.dataset.fresh = '1';
    }
    return lens;
  }

  /* Put the lens under `stage`'s chip; glide there unless `jump`. */
  function place(stage, ring, jump) {
    const af = row();
    const chip = chipOf(af, stage);
    if (!af || !chip) return;
    const lens = lensIn(af);
    const box = af.getBoundingClientRect(), r = chip.getBoundingClientRect();
    const k = box.width ? af.offsetWidth / box.width : 1;   // page zoom: window px to stage px
    const x = (r.left - box.left) * k, w = r.width * k;
    if (ring) lens.style.setProperty('--ring', ring);
    const moved = lens.dataset.stage && lens.dataset.stage !== stage;
    const instant = jump || lens.dataset.fresh === '1';
    lens.style.transition = instant ? 'none' : `transform ${MS}ms ${EASE}, width ${MS}ms ${EASE}`;
    lens.style.width = w + 'px';
    lens.style.transform = `translateX(${x}px)`;
    lens.dataset.stage = stage;
    delete lens.dataset.fresh;
    if (moved && !instant) {
      // The glass stretches along the way and settles when it lands.
      lens.classList.remove('flow'); void lens.offsetWidth; lens.classList.add('flow');
    }
  }

  function sync(jump) {
    const mark = document.querySelector('.st-key-gl-apps .af-mark');
    if (mark) place(mark.dataset.cur, mark.dataset.ring, jump);
  }

  // Glide at once on a click; the rerun that follows only confirms it.
  window.addEventListener('click', e => {
    const wrap = e.target.closest && e.target.closest('[class*="st-key-af-"]');
    const stage = wrap && stageOf(wrap);
    if (!stage || !wrap.closest('.st-key-gl-apps')) return;
    const color = getComputedStyle(wrap.querySelector('button'), '::before').backgroundColor;
    place(stage, stage === 'saved' ? '#8E8E93' : color, false);
  }, true);

  // Reruns replace the marker; follow it (and any layout change) without redrawing the lens.
  new MutationObserver(() => sync(false)).observe(document.body, { childList: true, subtree: true });
  window.addEventListener('resize', () => sync(true));

  window.__aaAppsFilter = { sync };
  requestAnimationFrame(() => sync(true));
})();
