/* Onboarding Profile step: a section card opens in full, flipping as it grows.
 *
 * Each card (.xp) carries everything it holds, uncut, in a hidden .xp-full
 * (views/onboarding.py). Pressing the card, or Enter/Space on it, lifts a copy
 * of it out of the page: the copy turns on its vertical axis while it grows
 * from the card's place to a panel in the middle of the window, and shows the
 * full content on its back. Esc, the close button or a press outside turn it
 * back into the card.
 *
 *  - Display only, but for one button: an editable card (data-edit) opens with
 *    a pencil that presses the hidden native button named there, which opens
 *    the editor on that section alone. The native buttons laid over a card
 *    (Edit profile, + Add …) sit above it and keep their clicks.
 *  - Updated ranking's roles open the same way. Their header is carried in
 *    .xp-full (.xp-head), their width in data-xp-width, and their "Start
 *    application" (data-apply) presses the hidden native button named there.
 *  - The page's stage is zoomed (--aa-k, ui/theme.py); the copy is zoomed the
 *    same way, so it reads at the card's own size.
 *  - With reduced motion the panel only fades in and out.
 */
(function () {
  if (window.__aaExpand) return;
  window.__aaExpand = 1;

  const DUR = 1000;        // ms, opening
  const DUR_BACK = 620;    // ms, closing
  const WIDTH = 560;       // stage px, the open panel
  const MARGIN = 48;       // stage px kept free around it
  const CURVE = 'cubic-bezier(.32,.72,0,1)';  // the iOS sheet curve, used where linear() is missing
  // The close glyph is drawn node by node: st.html() drops a script that spells out inline SVG.
  const NS = 'http://www.w3.org/2000/svg';
  function cross() {
    const g = document.createElementNS(NS, 'svg'), d = document.createElementNS(NS, 'path');
    [['width', 12], ['height', 12], ['viewBox', '0 0 16 16']].forEach(([k, v]) => g.setAttribute(k, v));
    [['d', 'M4 4l8 8M12 4l-8 8'], ['stroke', 'currentColor'], ['stroke-width', 2], ['stroke-linecap', 'round'], ['fill', 'none']]
      .forEach(([k, v]) => d.setAttribute(k, v));
    g.appendChild(d);
    return g;
  }
  function pencil() {
    const g = document.createElementNS(NS, 'svg'), d = document.createElementNS(NS, 'path');
    [['width', 13], ['height', 13], ['viewBox', '0 0 16 16']].forEach(([k, v]) => g.setAttribute(k, v));
    [['d', 'M10.5 2.5l3 3L6 13H3v-3z'], ['stroke', 'currentColor'], ['stroke-width', 1.6], ['stroke-linejoin', 'round'], ['fill', 'none']]
      .forEach(([k, v]) => d.setAttribute(k, v));
    g.appendChild(d);
    return g;
  }

  // A slightly underdamped spring, sampled into a linear() easing: the panel
  // grows a touch past its size, then settles on it.
  const SPRING = (() => {
    const w = 2 * Math.PI / 1.1, z = 0.74, n = 60, pts = [];
    const wd = w * Math.sqrt(1 - z * z);
    for (let i = 0; i <= n; i++) {
      const t = i / n * 1.4;
      const v = 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + z * w / wd * Math.sin(wd * t));
      pts.push(+v.toFixed(4));
    }
    pts[n] = 1;
    const css = `linear(${pts.join(',')})`;
    return CSS.supports('transition-timing-function', css) ? css : CURVE;
  })();

  const still = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const zoom = () => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--aa-k')) || 1;

  let open = null;  // {card, veil, fly, rot, back, busy}

  // Where the card sits, in the stage px the copy is laid out in.
  function box(el, k) {
    const r = el.getBoundingClientRect();
    return { left: r.left / k, top: r.top / k, width: r.width / k, height: r.height / k };
  }
  const px = b => ({ left: b.left + 'px', top: b.top + 'px', width: b.width + 'px', height: b.height + 'px' });

  function build(card) {
    const k = zoom();
    const veil = document.createElement('div');
    veil.className = 'xp-veil';

    const fly = document.createElement('div');
    fly.className = 'xp-fly';
    fly.style.zoom = k;
    fly.setAttribute('role', 'dialog');
    fly.setAttribute('aria-modal', 'true');
    const title = card.querySelector('.p-h b');
    fly.setAttribute('aria-label', title ? title.textContent : 'Details');

    // Front: the card as it is on the page, at its own size.
    const front = document.createElement('div');
    front.className = 'xp-face xp-front';
    const face = card.cloneNode(true);
    face.removeAttribute('role'); face.removeAttribute('tabindex'); face.removeAttribute('aria-label');
    face.querySelectorAll('.xp-full,.xp-ic').forEach(n => n.remove());
    face.classList.add('xp-copy');
    const b0 = box(card, k);
    face.style.width = b0.width + 'px';
    face.style.height = b0.height + 'px';
    front.appendChild(face);

    // Back: the header, everything the card holds, and where it came from.
    const back = document.createElement('div');
    back.className = 'xp-face xp-back';
    const inner = document.createElement('div');
    inner.className = 'xp-in';
    const head = card.querySelector('.p-h').cloneNode(true);
    const shut = document.createElement('button');
    shut.type = 'button'; shut.className = 'xp-x'; shut.appendChild(cross());
    shut.setAttribute('aria-label', 'Close');
    let edit = null;
    if (card.dataset.edit) {
      edit = document.createElement('button');
      edit.type = 'button'; edit.className = 'xp-x xp-ed'; edit.appendChild(pencil());
      const what = title ? title.textContent : 'this section';
      edit.setAttribute('aria-label', 'Edit ' + what); edit.title = 'Edit ' + what;
      edit.dataset.key = card.dataset.edit;
      head.appendChild(edit);
    }
    head.appendChild(shut);
    const body = document.createElement('div');
    body.className = 'xp-body';
    body.innerHTML = card.querySelector('.xp-full').innerHTML;
    body.querySelectorAll('.xp-head').forEach(n => n.remove());  // already cloned as the header
    const apply = body.querySelector('[data-apply]');
    inner.append(head, body);
    const src = card.querySelector('.p-src');
    if (src) inner.appendChild(src.cloneNode(true));
    back.appendChild(inner);

    const rot = document.createElement('div');
    rot.className = 'xp-rot';
    rot.append(front, back);
    fly.appendChild(rot);
    document.body.append(veil, fly);

    // Measure the back at the open width to know how tall the panel gets.
    const vw = window.innerWidth / k, vh = window.innerHeight / k;
    const w = Math.min(+card.dataset.xpWidth || WIDTH, vw - MARGIN);
    inner.style.width = w + 'px';
    const h = Math.min(inner.scrollHeight, vh - MARGIN * 2);
    const b1 = { left: (vw - w) / 2, top: (vh - h) / 2, width: w, height: h };
    Object.assign(fly.style, px(b0));
    return { card, veil, fly, rot, front, back, inner, shut, edit, apply, b0, b1 };
  }

  // The shadow deepens as the card leaves the page. It sits on the faces, so it turns with them.
  const LOW = '0 0 0 .5px rgba(0,0,0,.07), 0 4px 14px rgba(28,40,64,.05)';
  const HIGH = '0 0 0 .5px rgba(0,0,0,.06), 0 40px 90px rgba(28,40,64,.22), 0 8px 24px rgba(28,40,64,.10)';
  function lift(o, duration, easing, down) {
    const frames = down ? [{ boxShadow: HIGH }, { boxShadow: LOW }] : [{ boxShadow: LOW }, { boxShadow: HIGH }];
    [o.front, o.back].forEach(f => f.animate(frames, { duration, easing, fill: 'forwards' }));
  }

  function show(card) {
    if (open) return;
    const o = open = build(card);
    o.busy = true;
    o.returnTo = document.activeElement;
    card.classList.add('xp-away');
    o.veil.addEventListener('click', hide);
    o.shut.addEventListener('click', hide);
    if (o.edit) o.edit.addEventListener('click', () => {
      const native = document.querySelector('.st-key-' + o.edit.dataset.key + ' button');
      hide();
      if (native) native.click();
    });
    if (o.apply) o.apply.addEventListener('click', () => {
      const native = document.querySelector('.st-key-' + o.apply.dataset.apply + ' button');
      hide();
      if (native) native.click();
    });

    const done = () => {
      o.busy = false;
      o.fly.classList.add('xp-open');
      o.shut.focus({ preventScroll: true });
    };
    if (still()) {
      Object.assign(o.fly.style, px(o.b1));
      o.rot.style.transform = 'rotateY(180deg)';
      o.fly.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200 });
      o.veil.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, fill: 'forwards' });
      done();
      return;
    }
    o.veil.animate([{ opacity: 0 }, { opacity: 1 }], { duration: DUR * .6, easing: 'ease-out', fill: 'forwards' });
    o.fly.animate([px(o.b0), px(o.b1)], { duration: DUR, easing: SPRING, fill: 'forwards' });
    // The turn keeps its own pace, so it is seen: it gathers speed up to edge-on,
    // lifted towards the viewer, swings a few degrees past the back and settles.
    o.rot.animate([
      { transform: 'translateZ(0) rotateY(0deg)', easing: 'cubic-bezier(.5,0,.7,.4)' },
      { transform: 'translateZ(90px) rotateY(90deg)', offset: .4, easing: 'cubic-bezier(.2,.6,.35,1)' },
      { transform: 'translateZ(0) rotateY(187deg)', offset: .78, easing: 'ease-in-out' },
      { transform: 'translateZ(0) rotateY(180deg)' },
    ], { duration: DUR, fill: 'forwards' });
    o.front.firstChild.animate([{ opacity: 1 }, { opacity: 0, offset: .3 }, { opacity: 0 }], { duration: DUR, fill: 'forwards' });
    o.inner.animate([
      { opacity: 0, transform: 'translateY(10px)' },
      { opacity: 0, transform: 'translateY(10px)', offset: .42, easing: 'cubic-bezier(.2,.8,.2,1)' },
      { opacity: 1, transform: 'none', offset: .8 },
      { opacity: 1, transform: 'none' },
    ], { duration: DUR, fill: 'forwards' });
    lift(o, DUR, 'ease-out', false);
    setTimeout(done, DUR);
  }

  function hide() {
    const o = open;
    if (!o || o.busy) return;
    o.busy = true;
    o.fly.classList.remove('xp-open');
    o.back.scrollTop = 0;
    const end = () => {
      o.card.classList.remove('xp-away');
      o.veil.remove(); o.fly.remove();
      open = null;
      if (o.card.isConnected) o.card.focus({ preventScroll: true });
      else if (o.returnTo && o.returnTo.isConnected) o.returnTo.focus({ preventScroll: true });
    };
    // A rerun may have redrawn the card: fly back to where it is now.
    const home = o.card.isConnected ? box(o.card, zoom()) : null;
    if (still() || !home) {
      o.fly.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, fill: 'forwards' });
      o.veil.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, fill: 'forwards' }).onfinish = end;
      return;
    }
    // Commit where the opening left everything, then start the way back from there.
    [o.fly, o.rot, o.inner, o.front, o.back, o.front.firstChild].forEach(el =>
      el.getAnimations().forEach(a => { a.commitStyles(); a.cancel(); }));
    o.fly.animate([px(o.b1), px(home)], { duration: DUR_BACK, easing: CURVE, fill: 'forwards' });
    o.rot.animate([
      { transform: 'translateZ(0) rotateY(180deg)' },
      { transform: 'translateZ(60px) rotateY(90deg)', offset: .5 },
      { transform: 'translateZ(0) rotateY(0deg)' },
    ], { duration: DUR_BACK, easing: CURVE, fill: 'forwards' });
    o.inner.animate([{ opacity: 1 }, { opacity: 0, offset: .45 }, { opacity: 0 }], { duration: DUR_BACK, fill: 'forwards' });
    o.front.firstChild.animate([{ opacity: 0 }, { opacity: 0, offset: .5 }, { opacity: 1 }], { duration: DUR_BACK, fill: 'forwards' });
    lift(o, DUR_BACK, 'ease-in', true);
    o.veil.animate([{ opacity: 1 }, { opacity: 0 }], { duration: DUR_BACK * .8, easing: 'ease-in', fill: 'forwards' });
    setTimeout(end, DUR_BACK);
  }

  const target = e => {
    const c = e.target.closest && e.target.closest('.xp');
    return c && !c.classList.contains('xp-copy') ? c : null;
  };

  document.addEventListener('click', e => {
    const c = target(e);
    if (!c || open) return;
    if (e.target.closest('a,button,input,textarea,select')) return;
    e.preventDefault();
    show(c);
  });

  document.addEventListener('keydown', e => {
    if (open) {
      if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); hide(); }
      // Keep focus inside the panel: its edit, close and apply buttons are the only stops.
      else if (e.key === 'Tab') {
        e.preventDefault();
        const stops = [open.edit, open.shut, open.apply].filter(Boolean);
        const at = stops.indexOf(document.activeElement);
        stops[(at + (e.shiftKey ? stops.length - 1 : 1)) % stops.length].focus({ preventScroll: true });
      }
      return;
    }
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const c = target(e);
    if (!c || e.target !== c) return;
    e.preventDefault(); e.stopImmediatePropagation();
    show(c);
  }, true);
})();
