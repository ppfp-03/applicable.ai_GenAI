/*
 * Soundtrack playback through Web Audio. When sound is on, the audio clock is the master:
 * the picture reads its time from what the listener is hearing *now* (output latency
 * included), so every hit lands on its frame however long the film runs.
 *
 * The music is embedded as base64 (assets/soundtrack.js), so it decodes from file:// too.
 */
(function (A) {
  'use strict';

  class Soundtrack {
    constructor({ base64, mime, lead = 0 }) {
      this.base64 = base64;
      this.mime = mime;
      this.lead = lead; // measured decoder delay (tools/embed-audio.mjs), skipped at playback
      this.ctx = null;
      this.buffer = null;
      this.src = null;
      this.t0 = 0; // context time at which playhead 0 would have been heard
      this.gain = null;
    }

    /** Decode the embedded audio. Safe before any user gesture. */
    async load() {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx || !this.base64) return false;
      this.ctx = new Ctx({ latencyHint: 'playback' });
      const bin = atob(this.base64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      this.buffer = await this.ctx.decodeAudioData(bytes.buffer);
      this.gain = this.ctx.createGain();
      this.gain.connect(this.ctx.destination);
      return true;
    }

    /** True once the browser lets us make sound (after a gesture, or by policy). */
    async unlock() {
      if (!this.ctx) return false;
      if (this.ctx.state !== 'running') {
        try {
          await Promise.race([this.ctx.resume(), new Promise((r) => setTimeout(r, 250))]);
        } catch (e) {
          /* blocked until a gesture */
        }
      }
      return this.ctx.state === 'running';
    }

    get ready() {
      return !!(this.buffer && this.ctx && this.ctx.state === 'running');
    }

    play(offset) {
      this.stop();
      const src = this.ctx.createBufferSource();
      src.buffer = this.buffer;
      src.connect(this.gain);
      const when = this.ctx.currentTime + 0.05; // a little lead so the start is clean
      src.start(when, Math.max(0, offset + this.lead));
      this.t0 = when - offset;
      this.src = src;
    }

    stop() {
      if (this.src) {
        try {
          this.src.stop();
        } catch (e) {
          /* already stopped */
        }
        this.src.disconnect();
        this.src = null;
      }
    }

    /** Playhead of the audio being heard at this instant. */
    time() {
      const c = this.ctx;
      let heard = c.currentTime - (c.outputLatency || c.baseLatency || 0);
      if (c.getOutputTimestamp) {
        const ts = c.getOutputTimestamp();
        if (ts.contextTime > 0) heard = ts.contextTime + (performance.now() - ts.performanceTime) / 1000;
      }
      return heard - this.t0;
    }
  }

  A.Soundtrack = Soundtrack;
})(window.Applicable = window.Applicable || {});
