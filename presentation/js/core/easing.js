/* Easing curves. Every curve maps 0..1 to 0..1 (back curves overshoot slightly). */
(function (A) {
  'use strict';

  const clamp01 = (t) => (t < 0 ? 0 : t > 1 ? 1 : t);

  const ease = {
    linear: (t) => t,
    inSine: (t) => 1 - Math.cos((t * Math.PI) / 2),
    outSine: (t) => Math.sin((t * Math.PI) / 2),
    inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
    inCubic: (t) => t * t * t,
    outCubic: (t) => 1 - Math.pow(1 - t, 3),
    inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outQuart: (t) => 1 - Math.pow(1 - t, 4),
    inOutQuart: (t) => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2),
    outQuint: (t) => 1 - Math.pow(1 - t, 5),
    inOutQuint: (t) => (t < 0.5 ? 16 * Math.pow(t, 5) : 1 - Math.pow(-2 * t + 2, 5) / 2),
    outExpo: (t) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    inExpo: (t) => (t === 0 ? 0 : Math.pow(2, 10 * t - 10)),
    inOutExpo: (t) =>
      t === 0 ? 0 : t === 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2,
    // Restrained overshoot: a settle, not a bounce.
    outBack: (t) => {
      const c1 = 1.2;
      const c3 = c1 + 1;
      return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    },
    // Critically damped spring response, normalised to land exactly on 1.
    spring: (t) => {
      const w = 9;
      const v = 1 - (1 + w * t) * Math.exp(-w * t);
      const end = 1 - (1 + w) * Math.exp(-w);
      return v / end;
    },
  };

  A.ease = ease;
  A.clamp01 = clamp01;
  A.lerp = (a, b, t) => a + (b - a) * t;
  /** Normalised progress of t through [t0, t1], eased. */
  A.prog = (t, t0, t1, curve) => {
    const p = clamp01((t - t0) / (t1 - t0));
    return (typeof curve === 'function' ? curve : ease[curve || 'linear'])(p);
  };
})(window.Applicable = window.Applicable || {});
