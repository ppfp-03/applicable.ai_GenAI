/* Top bar: a floating liquid-glass capsule that survives page changes.
 *
 * Streamlit rebuilds every element when the page changes, the top bar
 * included. So the capsule the user sees is drawn by this script, outside
 * Streamlit's tree, and never rebuilt. The native `st.page_link` tabs stay in
 * the page, hidden, and are what the script clicks to navigate.
 *
 *  - A glass lens slides between the tabs; it can be pressed and dragged.
 *  - The five tabs all live on one page (ui/tabs.py): switching between them
 *    only changes which one is shown, and the URL. Nothing is rebuilt, and
 *    each tab keeps its scroll position. As on iOS, switching tab adds no
 *    history entry: Back leaves the tabs for the previous real page.
 *  - Going to any other page fades the content out and back in only once the
 *    new page has finished drawing, so it never shows half-built.
 *  - Scrolling, the capsule rises with the page, then sticks and compacts.
 */
(function () {
  if (window.__aaNav) return;
  window.__aaNav = 1;

  const H = document.documentElement;
  const SPRING = 'cubic-bezier(.3,1.3,.5,1)';
  const STICK = 12;               // px from the window top once stuck
  const QUIET = 160;              // ms without DOM changes = page finished drawing

  const real = () => document.querySelector('.st-key-cap');
  const scroller = () => document.querySelector('.stMain') || document.scrollingElement;
  const keyOf = el => { const m = / st-key-nav(?:-on)?-([\w-]+)/.exec(' ' + el.className); return m ? m[1] : ''; };
  const ratio = el => { const w = el.getBoundingClientRect().width; return w ? el.offsetWidth / w : 1; };

  // ───────────────────────── The floating capsule ─────────────────────────

  const nav = document.createElement('nav');
  nav.className = 'aa-nav';
  nav.setAttribute('aria-label', 'Main');
  // Built node by node: st.html drops a script that carries markup in a string.
  const cap = nav.appendChild(document.createElement('div'));
  cap.className = 'aa-cap';
  const lens = cap.appendChild(document.createElement('div'));
  lens.className = 'aa-lens';
  document.body.appendChild(nav);

  let active = '';                 // tab shown as active
  let sig = '';                    // labels last copied from the native tabs
  let lastPos = null;              // last place of the native capsule, for gaps

  const tab = k => cap.querySelector(`.aa-tab[data-k="${k}"]`);

  /* Copy the tabs (labels, badge counts, links) from the native capsule. */
  function copyTabs(r) {
    const items = [...r.querySelectorAll('[class*="st-key-nav"]')].map(c => {
      const a = c.querySelector('a'), p = a && (a.querySelector('p') || a);
      return { k: keyOf(c), html: p ? p.innerHTML : '', href: a ? a.getAttribute('href') || '' : '' };
    }).filter(t => t.k);
    const s = JSON.stringify(items);
    if (s === sig) return;
    sig = s;
    cap.querySelectorAll('.aa-tab').forEach(t => t.remove());
    items.forEach(t => {
      const a = document.createElement('a');
      a.className = 'aa-tab'; a.dataset.k = t.k; a.href = t.href || '#'; a.draggable = false;
      a.innerHTML = t.html;
      cap.appendChild(a);
    });
    lens.dataset.l = '';
  }

  /* Follow the native capsule while it is on screen; stick at the top after. */
  function position(r) {
    if (r) {
      const rr = r.getBoundingClientRect();
      if (rr.width) lastPos = { cx: rr.left + rr.width / 2, top: rr.top };
    }
    if (!lastPos) return;
    const k = ratio(nav) || 1;
    const top = Math.max(STICK, lastPos.top);
    nav.style.left = lastPos.cx * k + 'px';
    nav.style.top = top * k + 'px';
    nav.classList.toggle('stuck', lastPos.top < STICK - .5);
  }

  // ───────────────────────── Lens ─────────────────────────

  function box(a) {
    const k = ratio(cap), cr = cap.getBoundingClientRect(), r = a.getBoundingClientRect();
    return { l: (r.left - cr.left) * k, w: r.width * k, t: (r.top - cr.top) * k, h: r.height * k };
  }
  const lensNow = () => ({ l: parseFloat(getComputedStyle(lens).left) || 0 });

  /* The leading edge travels faster, so the lens stretches like a drop. */
  function put(b, mode, dir) {
    const st = lens.style;
    if (mode === 'jump') st.transition = 'none';
    else if (mode === 'follow') st.transition = 'left .14s ease-out,right .14s ease-out';
    else {
      const lead = '.34s', trail = '.52s';
      st.transition = `left ${dir > 0 ? trail : lead} ${SPRING},right ${dir > 0 ? lead : trail} ${SPRING},` +
        `top .3s ${SPRING},height .3s ${SPRING}`;
    }
    st.left = b.l + 'px';
    st.right = (cap.clientWidth - b.l - b.w) + 'px';
    st.top = b.t + 'px';
    st.height = b.h + 'px';
    lens.dataset.l = b.l; lens.dataset.w = b.w;
    if (mode === 'jump') { void lens.offsetWidth; st.transition = ''; }
  }

  function lensTo(k, mode) {
    const a = tab(k); if (!a) return;
    const to = box(a);
    if (mode !== 'jump' && lens.dataset.l === '') mode = 'jump';
    put(to, mode || 'slide', Math.sign(to.l - lensNow().l));
    cap.querySelectorAll('.aa-tab').forEach(t => t.classList.toggle('on', t.dataset.k === k));
  }

  // ───────────────────────── Page change ─────────────────────────

  let pending = null;              // { k, t } while a page is loading
  let lastMut = 0;

  function go(k) {
    if (hostMark() && TABS.includes(k)) { show(k); return; }
    if (k === active && !pending) { lensTo(k); return; }
    active = k;
    lensTo(k);
    const r = real();
    const a = r && [...r.querySelectorAll('[class*="st-key-nav"]')].find(c => keyOf(c) === k);
    const link = a && a.querySelector('a');
    if (!link) return;
    pending = { k, t: performance.now() };
    H.classList.add('aa-leaving');
    // Let the fade start before Streamlit begins tearing the page down.
    setTimeout(() => link.click(), 140);
    waitReady();
  }

  /* Reveal once the new page is the active one and has stopped changing. */
  function waitReady() {
    (function loop() {
      if (!pending) return;
      const r = real(), on = r && r.querySelector('[class*="st-key-nav-on"]');
      const now = performance.now();
      const arrived = on && keyOf(on) === pending.k && now - lastMut > QUIET && now - pending.t > 300;
      if (arrived || now - pending.t > 4000) {
        pending = null;
        scroller().scrollTop = 0;
        H.classList.remove('aa-leaving');
        sync();
        return;
      }
      requestAnimationFrame(loop);
    })();
  }

  // ───────────────────────── Tab host: instant switching ─────────────────────────

  const TABS = ['home', 'matches', 'applications', 'explore', 'profile'];
  const hostMark = () => document.querySelector('.aa-tabs');
  let shown = null, seenNonce = null;
  const scrolls = {};

  /* Streamlit's own href for each tab, read off the native capsule links. */
  function hrefs() {
    const out = {}, r = real();
    if (r) r.querySelectorAll('[class*="st-key-nav"]').forEach(c => {
      const a = c.querySelector('a'); if (a) out[keyOf(c)] = a.getAttribute('href') || '';
    });
    return out;
  }

  /* Absolute URL of a tab. The default page's link is empty: it is the root. */
  function tabUrl(k) {
    const h = hrefs();
    if (h[k]) return new URL(h[k], location.href).href;
    const other = Object.values(h).find(Boolean);
    if (!other) return null;
    const u = new URL(other, location.href);
    u.pathname = u.pathname.replace(/[^/]*$/, '');
    u.search = ''; u.hash = '';
    return u.href;
  }

  const bare = u => { const x = new URL(u, location.href); return x.origin + x.pathname.replace(/\/$/, ''); };
  const tabAt = url => TABS.find(k => { const t = tabUrl(k); return t && bare(t) === bare(url); }) || null;

  let own = false;   // true while this script itself writes the URL

  /* Bring a tab to the front and put its URL in the address bar. */
  function show(k) {
    const sc = scroller(), changed = shown !== k;
    if (shown && changed) scrolls[shown] = sc.scrollTop;
    shown = k; active = k;
    H.dataset.tab = k;
    lensTo(k);
    if (changed) {
      sc.scrollTop = scrolls[k] || 0;
      window.dispatchEvent(new Event('resize'));   // hidden tabs measured 0 wide
    }
    const url = tabUrl(k);
    if (url && bare(url) !== bare(location.href)) {
      own = true;
      try { history.replaceState(history.state, '', url); } finally { own = false; }
    }
  }

  // After each run Streamlit writes the URL of the page it believes is shown.
  // In the tab host that is whichever tab the page was loaded on, not the one
  // in front: keep the address on the tab in front, and add no history entry.
  ['pushState', 'replaceState'].forEach(fn => {
    const orig = history[fn].bind(history);
    history[fn] = function (state, title, url) {
      if (!own && url != null && shown && hostMark()) {
        const k = tabAt(new URL(url, location.href).href);
        if (k && k !== shown) return;
      }
      return orig(state, title, url);
    };
  });

  /* Returns true while the tab host is on the page (it then owns the lens). */
  function syncHost() {
    const m = hostMark();
    if (!m) { shown = null; seenNonce = null; delete H.dataset.tab; return false; }
    // First sight of the host, or the server asked for a tab (go() in Python).
    if (shown === null || m.dataset.nonce !== seenNonce) {
      if (!tab(m.dataset.active)) return true;   // capsule not drawn yet: next sync
      seenNonce = m.dataset.nonce;
      show(m.dataset.active);
    } else if (!drag && !pending && tab(shown)) {
      const b = box(tab(shown));
      if (lens.dataset.l === '' || Math.abs(+lens.dataset.l - b.l) > 1 || Math.abs(+lens.dataset.w - b.w) > 1) lensTo(shown, lens.dataset.l === '' ? 'jump' : 'slide');
    }
    return true;
  }

  // ───────────────────────── Keeping in step with Streamlit ─────────────────────────

  function sync() {
    const r = real();
    if (!r) {
      // No top bar on this page (onboarding), unless one is on its way.
      if (!pending) nav.classList.add('gone');
      return;
    }
    nav.classList.remove('gone');
    H.classList.add('aa-nav-float');
    copyTabs(r);
    position(r);
    if (syncHost()) { lens.style.opacity = ''; return; }
    if (pending || drag) return;
    const on = r.querySelector('[class*="st-key-nav-on"]');
    const k = on ? keyOf(on) : '';
    if (!k || !tab(k)) { lens.style.opacity = 0; active = ''; return; }
    lens.style.opacity = '';
    const b = box(tab(k));
    const moved = k !== active || lens.dataset.l === '' || Math.abs(+lens.dataset.l - b.l) > 1 || Math.abs(+lens.dataset.w - b.w) > 1;
    active = k;
    if (moved) lensTo(k, lens.dataset.l === '' ? 'jump' : 'slide');
  }

  // ───────────────────────── Input ─────────────────────────

  let drag = null, swallow = false;

  function nearest(x) {
    let best = null, d = Infinity;
    cap.querySelectorAll('.aa-tab').forEach(a => { const b = box(a), e = Math.abs(b.l + b.w / 2 - x); if (e < d) { d = e; best = a; } });
    return best;
  }

  cap.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    const a = e.target.closest('.aa-tab');
    lens.classList.add('press');
    if (a) lensTo(a.dataset.k);
    drag = { x0: e.clientX, k: ratio(cap), on: false };
  });

  window.addEventListener('pointermove', e => {
    if (!drag) return;
    if (!drag.on) { if (Math.abs(e.clientX - drag.x0) < 4) return; drag.on = true; H.classList.add('aa-dragging'); }
    const x = (e.clientX - cap.getBoundingClientRect().left) * drag.k;
    const b = box(nearest(x));
    const l = Math.max(4, Math.min(cap.clientWidth - 4 - b.w, x - b.w / 2));
    put({ ...b, l }, 'follow');
  }, true);

  function release() {
    if (!drag) return;
    const was = drag;
    drag = null;
    lens.classList.remove('press');
    H.classList.remove('aa-dragging');
    if (!was.on) { setTimeout(() => { if (!pending) lensTo(active); }, 350); return; }
    swallow = true;
    setTimeout(() => { swallow = false; }, 80);
    go(nearest(+lens.dataset.l + +lens.dataset.w / 2).dataset.k);
  }
  window.addEventListener('pointerup', release, true);
  window.addEventListener('pointercancel', release, true);

  cap.addEventListener('click', e => {
    const a = e.target.closest('.aa-tab'); if (!a) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;   // new tab: let the link work
    e.preventDefault();
    if (swallow) { swallow = false; return; }
    go(a.dataset.k);
  });

  // Links to a tab anywhere in the page ("See all") switch in place too.
  window.addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a || nav.contains(a) || a.closest('.st-key-cap') || !hostMark()) return;
    const raw = a.getAttribute('href') || '', h = hrefs();
    const k = TABS.find(t => t in h && h[t] === raw);
    if (!k) return;
    e.preventDefault(); e.stopImmediatePropagation();
    show(k);
  }, true);

  // ───────────────────────── Wiring ─────────────────────────

  let queued = false;
  const schedule = () => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; sync(); }); };
  new MutationObserver(ms => {
    if (ms.some(m => !nav.contains(m.target))) { lastMut = performance.now(); schedule(); }
  }).observe(document.body, { childList: true, subtree: true });
  window.addEventListener('resize', schedule);
  window.addEventListener('scroll', () => position(real()), { capture: true, passive: true });
  // The capsule sits outside Streamlit's scroller; a wheel over it still scrolls the page.
  nav.addEventListener('wheel', e => { e.preventDefault(); scroller().scrollBy(e.deltaX, e.deltaY); }, { passive: false });
  schedule();
})();
