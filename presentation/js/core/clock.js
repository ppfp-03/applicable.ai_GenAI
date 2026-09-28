/*
 * Playback clock. Maps wall time (or, with sound, the audio being heard) to playhead time and
 * calls onFrame(t) once per display frame. Pauses itself while the tab is hidden so the film
 * never "plays unseen".
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
      this.audio = null; // a ready Soundtrack becomes the master clock
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
    get synced() {
      return !!(this.audio && this.audio.ready);
    }
    play() {
      if (this.playing) return;
      if (this.t >= this.duration) this.t = 0;
      this.playing = true;
      this._origin = performance.now() - this.t * 1000;
      if (this.synced) this.audio.play(this.t);
      this._raf = requestAnimationFrame(this._tick);
    }
    pause() {
      this.playing = false;
      cancelAnimationFrame(this._raf);
      if (this.audio) this.audio.stop();
    }
    seek(t) {
      this.t = Math.max(0, Math.min(this.duration, t));
      this._origin = performance.now() - this.t * 1000;
      if (this.playing && this.synced) this.audio.play(this.t);
      this.onFrame(this.t);
    }
    _tick(now) {
      if (!this.playing) return;
      // Audio time is only trusted forwards: never step the picture back by a latency jitter.
      const t = this.synced ? Math.max(this.t, this.audio.time()) : (now - this._origin) / 1000;
      this.t = Math.min(this.duration, Math.max(0, t));
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
