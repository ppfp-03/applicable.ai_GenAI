// The guided tour's dim and card placement (ui/tour.py).
//
// Every frame: find the tour marker; if there is none, take the dim away.
// Otherwise light up the element the marker names — a veil over the page,
// with a hole the size of the element — and put the tour card beside it.
// The veil takes the clicks, so only the card's buttons work during the tour.
(function () {
  if (window.__aaTour) return;
  window.__aaTour = 1;
  const D = document;
  let veil = null, hole = null, lastStep = null;

  function drop() {
    if (veil) { veil.remove(); hole.remove(); veil = hole = null; lastStep = null; }
  }

  function make() {
    if (veil) return;
    veil = D.createElement('div'); veil.className = 'aa-tour-veil';
    hole = D.createElement('div'); hole.className = 'aa-tour-hole';
    D.body.append(veil, hole);
  }

  function frame() {
    const mark = D.querySelector('.aa-tour-mark');
    const card = D.querySelector('.st-key-tour');
    if (!mark || !card) { drop(); return requestAnimationFrame(frame); }
    make();
    // Rects come back in screen pixels; styles are set in CSS pixels, which
    // the page zoom (ui/theme.py) scales. The veil spans the window: the
    // ratio between its two widths is that zoom.
    const z = veil.getBoundingClientRect().width / (veil.offsetWidth || 1) || 1;
    const vw = veil.offsetWidth, vh = veil.offsetHeight;
    const target = D.querySelector(mark.dataset.sel);
    if (!target) { hole.style.opacity = 0; return requestAnimationFrame(frame); }
    if (mark.dataset.step !== lastStep) {
      lastStep = mark.dataset.step;
      const r0 = target.getBoundingClientRect();
      if (r0.top < 0 || r0.bottom > window.innerHeight) target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    const r = target.getBoundingClientRect(), pad = 10;
    const L = r.left / z - pad, T = r.top / z - pad, W = r.width / z + 2 * pad, H = r.height / z + 2 * pad;
    Object.assign(hole.style, { opacity: 1, left: L + 'px', top: T + 'px', width: W + 'px', height: H + 'px' });

    // The card: under the element if it fits, else above, else beside it.
    const cw = card.offsetWidth, ch = card.offsetHeight, gap = 18;
    let x = Math.min(Math.max(16, L), vw - cw - 16), y;
    if (T + H + gap + ch < vh - 16) y = T + H + gap;
    else if (T - gap - ch > 16) y = T - gap - ch;
    else {
      y = Math.min(Math.max(16, T), vh - ch - 16);
      x = L + W + gap + cw < vw - 16 ? L + W + gap : Math.max(16, L - gap - cw);
    }
    card.style.left = x + 'px';
    card.style.top = y + 'px';
    card.classList.add('aa-placed');
    requestAnimationFrame(frame);
  }
  frame();
})();
