/* Explore's pager: a liquid-glass capsule with a lens under the current page.
 *
 * The same lens as Home's Applications chips (ui/js/apps_filter.js): made
 * here once and kept across reruns, it glides to the pressed number at once,
 * stretching as it moves, and the rerun confirms it through the marker the
 * page renders (.xp-mark data-cur). The arrows move it one number along.
 * Turning a page also names its direction on the html element, so the new
 * cards slide in from the side the user is heading to.
 *
 * Keep "less-than followed by a letter or slash" out of this file, comments
 * included: Streamlit sanitises st.html with DOMPurify, which drops a whole
 * script whose text looks like it contains a tag.
 */
(function () {
  if (window.__aaPager) { window.__aaPager.sync(false); return; }

  const EASE = 'cubic-bezier(.3,1.35,.5,1)';   // a little overshoot, like glass settling
  const MS = 520;

  const bar = () => document.querySelector('.st-key-x-pager');
  const numOf = el => { const m = / st-key-x-pg-(\d+)/.exec(' ' + (el.className || '')); return m ? +m[1] : null; };
  const btnOf = (pg, n) => pg && pg.querySelector('.st-key-x-pg-' + n);
  const curOf = pg => { const m = pg && pg.querySelector('.xp-mark'); return m ? +m.dataset.cur : null; };

  function lensIn(pg) {
    let lens = pg.querySelector(':scope > .xp-lens');
    if (!lens) {
      lens = document.createElement('span');  // not a div: the pager's row rules style every child div
      lens.className = 'xp-lens';
      lens.appendChild(document.createElement('i'));
      pg.prepend(lens);
      pg.classList.add('has-lens');
      lens.dataset.fresh = '1';
    }
    return lens;
  }

  /* Put the lens under page n's number; glide there unless `jump`. */
  function place(n, jump) {
    const pg = bar();
    const btn = btnOf(pg, n);
    if (!pg || !btn) return;
    const lens = lensIn(pg);
    const box = pg.getBoundingClientRect(), r = btn.getBoundingClientRect();
    const k = box.width ? pg.offsetWidth / box.width : 1;   // page zoom: window px to stage px
    const x = (r.left - box.left - pg.clientLeft) * k, y = (r.top - box.top - pg.clientTop) * k;
    const moved = lens.dataset.n && lens.dataset.n !== String(n);
    const instant = jump || lens.dataset.fresh === '1' || !box.width;
    lens.style.transition = instant ? 'none' : `transform ${MS}ms ${EASE}, width ${MS}ms ${EASE}`;
    lens.style.width = r.width * k + 'px';
    lens.style.height = r.height * k + 'px';
    lens.style.transform = `translate(${x}px, ${y}px)`;
    lens.dataset.n = String(n);
    if (box.width) delete lens.dataset.fresh;
    if (moved && !instant) {
      // The glass stretches along the way and settles when it lands.
      lens.classList.remove('flow'); void lens.offsetWidth; lens.classList.add('flow');
    }
  }

  // After a click the lens already sits on the new page; until the rerun's
  // marker agrees, the old marker must not pull it back.
  let pending = null, until = 0;

  // A hidden tab lays the pager out at zero size; measure again once it shows.
  const seen = new WeakSet();
  const ro = new ResizeObserver(() => sync(true));

  function sync(jump) {
    const pg = bar();
    if (pg && !seen.has(pg)) { seen.add(pg); ro.observe(pg); }
    const n = curOf(pg);
    if (n === null) return;
    if (pending !== null && n !== pending && Date.now() < until) return;
    pending = null;
    place(n, jump);
  }

  // Glide at once on a click; the rerun that follows only confirms it.
  window.addEventListener('click', e => {
    const pg = bar();
    const wrap = pg && e.target.closest && e.target.closest('.st-key-x-pager [class*="st-key-x-pg-"]');
    if (!wrap || wrap.querySelector('button:disabled')) return;
    const cur = curOf(pg);
    const lens = pg.querySelector(':scope > .xp-lens');
    const from = lens && lens.dataset.n ? +lens.dataset.n : cur;
    const cls = ' ' + wrap.className;
    const to = cls.includes(' st-key-x-pg-prev') ? from - 1 : cls.includes(' st-key-x-pg-next') ? from + 1 : numOf(wrap);
    if (to === null || to === from) return;
    document.documentElement.dataset.xpDir = to > from ? 'next' : 'prev';
    pending = to; until = Date.now() + 3000;
    if (btnOf(pg, to)) place(to, false);
  }, true);

  // Reruns replace the marker; follow it (and any layout change) without redrawing the lens.
  new MutationObserver(() => sync(false)).observe(document.body, { childList: true, subtree: true });
  window.addEventListener('resize', () => sync(true));

  window.__aaPager = { sync };
  requestAnimationFrame(() => sync(true));
})();
