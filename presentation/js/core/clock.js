/*
 * Playback clock. Maps wall time to playhead time and calls onFrame(t) once per display
 * frame. Pauses itself while the tab is hidden so the film never "jumps ahead" unseen.
 */
(function (A) {
  'use strict';

  class Clock {
    constructor({ duration, onFrame, onEnd }) {
      this.duration = duration;
      this.onFrame = onFrame;
      this.onEnd = onEnd;
      this.t = 0;
      this.playing = false;
      this.rate = 1;
      this._raf = 0;
      this._origin = 0; // performance.now() at which t would have been 0
      this._tick = this._tick.bind(this);
      this._hiddenWhilePlaying = false;
      document.addEventListener('visibilitychange', () => {
        if (document.hidden && this.playing) {
          this._hiddenWhilePlaying = true;
          this.pause();
        } else if (!document.hidden && this._hiddenWhilePlaying) {
          this._hiddenWhilePlaying = false;
          this.play();
        }
      });
    }
    play() {
      if (this.playing) return;
      if (this.t >= this.duration) this.t = 0;
      this.playing = true;
      this._origin = performance.now() - (this.t * 1000) / this.rate;
      this._raf = requestAnimationFrame(this._tick);
    }
    pause() {
      this.playing = false;
      cancelAnimationFrame(this._raf);
    }
    seek(t) {
      this.t = Math.max(0, Math.min(this.duration, t));
      this._origin = performance.now() - (this.t * 1000) / this.rate;
      this.onFrame(this.t);
    }
    _tick(now) {
      if (!this.playing) return;
      this.t = Math.min(this.duration, ((now - this._origin) / 1000) * this.rate);
      this.onFrame(this.t);
      if (this.t >= this.duration) {
        this.playing = false;
        if (this.onEnd) this.onEnd();
        return;
      }
      this._raf = requestAnimationFrame(this._tick);
    }
  }

  A.Clock = Clock;
})(window.Applicable = window.Applicable || {});
