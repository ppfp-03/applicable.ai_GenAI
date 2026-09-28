/*
 * Minimal deck: just enough to prove the hand-off. Slide 0 is the trailer's final frame
 * (the cover); the following slides are the <section class="slide"> elements in #deck.
 *
 * Input (only while enabled, i.e. in PRESENTATION_READY):
 *   keyboard  → ↓ PageDown Space Enter = next · ← ↑ PageUp Backspace = previous · Home/End
 *   click     anywhere = next (left fifth of the screen = previous)
 *   trackpad  horizontal swipe (wheel deltaX)
 *   touch     horizontal swipe
 * Going back to slide 0 shows the cover; it never restarts the film.
 */
(function (A) {
  'use strict';

  class Deck {
    constructor({ cover, root, hint, counter }) {
      this.cover = cover;
      this.slides = [cover, ...root.querySelectorAll('.slide')];
      this.hint = hint;
      this.counter = counter;
      this.index = 0;
      this.enabled = false;
      this._wheel = 0;
      this._wheelLock = 0;
      this._bind();
      this._render(true);
    }

    enable() {
      this.enabled = true;
      this.hint.classList.add('is-visible');
    }
    disable() {
      this.enabled = false;
      this.hint.classList.remove('is-visible');
    }
    next() {
      this.go(this.index + 1);
    }
    prev() {
      this.go(this.index - 1);
    }
    go(i, { instant = false } = {}) {
      const to = Math.max(0, Math.min(this.slides.length - 1, i));
      if (to === this.index && !instant) return;
      const dir = Math.sign(to - this.index) || 1;
      const from = this.slides[this.index];
      this.index = to;
      if (to > 0) this.hint.classList.remove('is-visible');
      this._render(instant, from, dir);
      document.dispatchEvent(new CustomEvent('applicable:slidechange', { detail: { index: to } }));
    }

    _render(instant, from, dir = 1) {
      const cur = this.slides[this.index];
      this.slides.forEach((s) => {
        s.classList.toggle('is-current', s === cur);
        s.setAttribute('aria-hidden', s === cur ? 'false' : 'true');
      });
      this.counter.textContent = this.index === 0 ? '' : `${this.index + 1} / ${this.slides.length}`;
      if (instant || !from || from === cur || !cur.animate) {
        this.slides.forEach((s) => s.getAnimations && s.getAnimations().forEach((a) => a.cancel()));
        return;
      }
      const opts = { duration: 520, easing: 'cubic-bezier(.65,0,.35,1)', fill: 'both' };
      from.animate([{ transform: 'translateX(0)', opacity: 1 }, { transform: `translateX(${-dir * 80}px)`, opacity: 0 }], opts);
      cur.animate([{ transform: `translateX(${dir * 80}px)`, opacity: 0 }, { transform: 'translateX(0)', opacity: 1 }], opts);
    }

    _bind() {
      const NEXT = ['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'];
      const PREV = ['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'];
      window.addEventListener('keydown', (e) => {
        if (!this.enabled || e.metaKey || e.ctrlKey || e.altKey) return;
        if (NEXT.includes(e.key)) this.next();
        else if (PREV.includes(e.key)) this.prev();
        else if (e.key === 'Home') this.go(0);
        else if (e.key === 'End') this.go(this.slides.length - 1);
        else return;
        e.preventDefault();
      });
      window.addEventListener('click', (e) => {
        if (!this.enabled || e.button !== 0 || e.target.closest('a, button, input, [data-no-advance]')) return;
        if (e.clientX < window.innerWidth / 5) this.prev();
        else this.next();
      });
      window.addEventListener(
        'wheel',
        (e) => {
          if (!this.enabled || Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
          e.preventDefault();
          const now = performance.now();
          if (now < this._wheelLock) return;
          this._wheel += e.deltaX;
          if (Math.abs(this._wheel) > 60) {
            this._wheel > 0 ? this.next() : this.prev();
            this._wheel = 0;
            this._wheelLock = now + 650; // one slide per gesture (inertia keeps firing)
          }
        },
        { passive: false }
      );
      let t0 = null;
      window.addEventListener('touchstart', (e) => (t0 = e.touches.length === 1 ? [e.touches[0].clientX, e.touches[0].clientY] : null), { passive: true });
      window.addEventListener('touchend', (e) => {
        if (!this.enabled || !t0) return;
        const dx = e.changedTouches[0].clientX - t0[0], dy = e.changedTouches[0].clientY - t0[1];
        t0 = null;
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.2) dx < 0 ? this.next() : this.prev();
      });
    }
  }

  A.Deck = Deck;
})(window.Applicable = window.Applicable || {});
