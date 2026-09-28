/*
 * Fixed 1920×1080 stage, letterboxed and scaled to fit the viewport. Everything inside is
 * authored in stage pixels, so the composition is identical at any window size.
 */
(function (A) {
  'use strict';

  const W = 1920;
  const H = 1080;

  function fitStage(stage) {
    const apply = () => {
      const s = Math.min(window.innerWidth / W, window.innerHeight / H);
      stage.style.setProperty('--stage-scale', String(s));
      stage.style.left = Math.round((window.innerWidth - W * s) / 2) + 'px';
      stage.style.top = Math.round((window.innerHeight - H * s) / 2) + 'px';
    };
    apply();
    window.addEventListener('resize', apply);
    return apply;
  }

  /** Small DOM helper: h('div.card.is-go', {style}, children…). */
  function h(tag, attrs, ...children) {
    const [name, ...classes] = tag.split('.');
    const el = document.createElement(name || 'div');
    if (classes.length) el.className = classes.join(' ');
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        if (k === 'style') Object.assign(el.style, attrs.style);
        else if (k === 'html') el.innerHTML = attrs.html;
        else if (k === 'text') el.textContent = attrs.text;
        else el.setAttribute(k, attrs[k]);
      }
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  /** Deterministic PRNG (mulberry32), so procedural layouts are identical on every load. */
  function rng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  A.STAGE = { W, H };
  A.fitStage = fitStage;
  A.h = h;
  A.rng = rng;
})(window.Applicable = window.Applicable || {});
