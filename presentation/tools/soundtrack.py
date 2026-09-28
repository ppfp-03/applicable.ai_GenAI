#!/usr/bin/env python3
"""
Applicable.ai opening film — score and sound design, synthesized from code.

Reads audio/cues.json (exported from the same timeline the picture uses, tools/export-cues.mjs)
and writes audio/soundtrack.wav (48 kHz stereo). Deterministic: re-running reproduces the mix.

The score follows the story, on a 120 BPM grid (bar = 2 s):
  0–19.5 s   the problem   D minor. A clock that ticks, a task motif per verb, an ostinato
                            that tightens and accelerates while the desk fills up.
  19.5 s     the freeze    everything stops dead; one low hit on "And then it gets harder."
  22–30 s    abroad        a dissonant drone and a slow heartbeat; each constraint lands low.
  30–33 s    the question  near-silence, one thin high note; the tile arrives with a bell.
  33 s →     the answer    the same key opens into D major: warm pad, felt-piano arpeggio,
                            soft pulse; the interface sounds are consonant from here on.
  57.5 s     the promise   a final D(add9) that rings out over the lockup.

DSP helpers (buffers, filters, PolyBLEP saw, convolution reverb, FM bell, whoosh, pluck,
limiter) are adapted from the reference film's soundtrack.py — Leonxlnx/claude-launchvideo,
MIT License, Copyright (c) 2026 Leonxlnx. See tools/THIRD_PARTY_NOTICES.md.
"""
import json
import os

import numpy as np
from scipy import signal

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUES = json.load(open(os.path.join(ROOT, 'audio', 'cues.json')))
M = CUES['marks']
END = CUES['duration']
DUR = END + 1.0
N = int(DUR * SR)
BEAT = 60.0 / CUES['bpm']
BAR = 4 * BEAT
rng = np.random.default_rng(11)


def bar(n, beat=0.0):
    """1-indexed bar, beat offset → seconds."""
    return (n - 1) * BAR + beat * BEAT


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------------------------------
# buffers and DSP (adapted from the reference, MIT)
# ---------------------------------------------------------------------------------------
def buf():
    return np.zeros((N, 2))


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(dst, x, t, gain=1.0, pan=0.0):
    """Add mono or stereo x into dst at time t (s) with constant-power pan and a tiny fade-out."""
    i = int(round(t * SR))
    if i >= N or len(x) == 0:
        return
    if x.ndim == 1:
        a = (pan + 1) * np.pi / 4
        x = np.stack([x * np.cos(a), x * np.sin(a)], axis=1)
    x = x.copy()
    nf = min(len(x), int(0.006 * SR))
    x[-nf:] *= (np.cos(np.linspace(0, np.pi / 2, nf)) ** 2)[:, None]
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), N - i)
    dst[i:i + n] += x[:n] * gain


def sos_lp(f, order=2):
    return signal.butter(order, min(f, SR * 0.45), 'low', fs=SR, output='sos')


def sos_hp(f, order=2):
    return signal.butter(order, max(f, 10), 'high', fs=SR, output='sos')


def sos_bp(lo, hi, order=2):
    return signal.butter(order, [max(lo, 10), min(hi, SR * 0.45)], 'band', fs=SR, output='sos')


def filt(x, sos):
    return signal.sosfilt(sos, x, axis=0)


def sweep_filter(x, cutoffs, kind='low', order=2, block=256):
    """Time-varying filter; cutoffs is a per-sample array of Hz."""
    y = np.zeros_like(x)
    zi = None
    for s in range(0, len(x), block):
        c = float(np.mean(cutoffs[s:s + block]))
        sos = sos_lp(c, order) if kind == 'low' else sos_hp(c, order) if kind == 'high' else sos_bp(c / 1.35, c * 1.35, order)
        if zi is None:
            zi = np.zeros((sos.shape[0], 2) + x.shape[1:])
        y[s:s + block], zi = signal.sosfilt(sos, x[s:s + block], axis=0, zi=zi)
    return y


def noise(d):
    return rng.standard_normal(int(d * SR))


def adsr(d, a=0.005, dcy=0.1, s=0.7, r=0.2):
    n = int(d * SR)
    env = np.ones(n) * s
    na, nd, nr = max(1, min(int(a * SR), n)), int(dcy * SR), int(r * SR)
    env[:na] = np.linspace(0, 1, na)
    if na + nd < n:
        env[na:na + nd] = np.linspace(1, s, nd)
    if 0 < nr < n:
        env[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return env


def saw_blep(freq, d, phase0=0.0):
    """PolyBLEP band-limited saw."""
    n = int(d * SR)
    f = np.full(n, freq) if np.isscalar(freq) else freq[:n]
    dt = f / SR
    ph = (phase0 + np.cumsum(dt)) % 1.0
    y = 2 * ph - 1
    m1 = ph < dt
    t1 = ph[m1] / dt[m1]
    y[m1] -= t1 + t1 - t1 * t1 - 1
    m2 = ph > 1 - dt
    t2 = (ph[m2] - 1) / dt[m2]
    y[m2] -= t2 * t2 + t2 + t2 + 1
    return y


def sine(freq, d, phase0=0.0):
    n = int(d * SR)
    f = np.full(n, freq) if np.isscalar(freq) else freq[:n]
    return np.sin(2 * np.pi * (phase0 + np.cumsum(f) / SR))


def sat(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


def make_ir(rt60=2.4, pre=0.02, lp=6500, width=1.0, seed=3):
    r = np.random.default_rng(seed)
    n = int(rt60 * 1.2 * SR)
    t = np.arange(n) / SR
    ir = np.stack([r.standard_normal(n), r.standard_normal(n)], axis=1) * np.exp(-6.9 * t / rt60)[:, None]
    ir = filt(ir, sos_lp(lp, 1))
    mid = ir.mean(axis=1, keepdims=True)
    ir = mid + (ir - mid) * width
    ir = np.concatenate([np.zeros((int(pre * SR), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2))


IR_HALL = make_ir(3.2, 0.03, 5000, 1.0, 3)
IR_ROOM = make_ir(0.8, 0.01, 7000, 0.8, 5)


def reverb(x, ir):
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    return np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in (0, 1)], axis=1)


# ---------------------------------------------------------------------------------------
# instruments
# ---------------------------------------------------------------------------------------
def tick(freq=3200, d=0.05, tau=0.006, body=0.6):
    t = tt(d)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / tau) * body + filt(noise(d), sos_hp(5000)) * np.exp(-t / 0.0015) * 0.5


def tock(freq=1100, d=0.14, tau=0.03, low=0.4):
    """Wooden knock: a resonant band plus a small low thump."""
    t = tt(d)
    res = filt(noise(d) * np.exp(-t / 0.004), sos_bp(freq * 0.85, freq * 1.18, 2)) * 6 * np.exp(-t / tau)
    return res + np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.025) * low


def kick(d=0.8, hard=1.0):
    t = tt(d)
    f = mtof(26) + 90 * np.exp(-t / 0.035) + 30 * np.exp(-t / 0.006)  # settles on D1
    body = sine(f, d) * np.exp(-t / (0.22 * hard + 0.05))
    click = filt(noise(d), sos_hp(2500)) * np.exp(-t / 0.0025) * 0.25
    return sat(body * 1.1 + click, 1.6) * 0.9


def sub_boom(d=3.0, f0=55, f1=36.7, glide=0.5):
    t = tt(d)
    f = f1 + (f0 - f1) * np.exp(-t / glide)
    x = sat(sine(f, d) * np.exp(-t / 1.0) + sine(f * 2, d) * np.exp(-t / 0.3) * 0.25, 1.4)
    return x * 0.9 + filt(noise(d), sos_lp(160, 2)) * np.exp(-t / 0.06) * 0.6


def hat(d=0.1, tau=0.016, bright=7800):
    t = tt(d)
    ring = sum(np.sin(2 * np.pi * f * t) for f in (8100, 10900, 13300)) * 0.06
    return (filt(noise(d), sos_hp(bright, 2)) + ring) * np.exp(-t / tau) * 0.45


def ui_click(d=0.25):
    t = tt(d)
    c = filt(noise(d), sos_hp(3000)) * np.exp(-t / 0.0012)
    return c * 0.8 + np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.03) * 0.35 + np.sin(2 * np.pi * (95 + 40 * np.exp(-t / 0.01)) * t) * np.exp(-t / 0.05) * 0.7


def key_click(seed):
    r = np.random.default_rng(seed)
    d = 0.05
    t = tt(d)
    f = 2400 + r.random() * 2200
    x = filt(noise(d), sos_bp(f * 0.7, f * 1.3, 2)) * np.exp(-t / (0.004 + r.random() * 0.004))
    return (x + np.sin(2 * np.pi * (180 + r.random() * 60) * t) * np.exp(-t / 0.012) * 0.25) * (0.55 + r.random() * 0.35)


def fm_bell(midi, d=3.0, idx=2.0, ratio=3.5, tau=1.2):
    d = max(d, 5 * tau)
    t = tt(d)
    fc = mtof(midi)
    mod = np.sin(2 * np.pi * fc * ratio * t) * idx * np.exp(-t / 0.35)
    x = np.sin(2 * np.pi * fc * t + mod) * np.exp(-t / tau) + np.sin(2 * np.pi * fc * 2.0 * t) * np.exp(-t / (tau * 0.35)) * 0.15
    return x * np.minimum(1, t / 0.003)


def whoosh(d=0.8, f0=180, f1=1400, f2=300, peak=0.55, width=1.0, air=0.1):
    """Camera-move whoosh: coloured noise through a moving band; `peak` = fastest moment."""
    n = int(d * SR)
    u = np.arange(n) / SR / d
    cut = np.where(u < peak, f0 * (f1 / f0) ** (u / peak), f1 * (f2 / f1) ** ((u - peak) / (1 - peak)))

    def coloured():
        w = noise(d)
        brown = filt(np.cumsum(w), sos_hp(30, 2))
        brown /= np.max(np.abs(brown)) + 1e-9
        return brown * 0.7 + filt(w, sos_lp(4000, 1)) * 0.3

    y = sweep_filter(np.stack([coloured(), coloured()], axis=1), cut, 'band') * 2.2
    y += filt(np.stack([noise(d), noise(d)], axis=1), sos_hp(4000, 2)) * air
    env = np.where(u < peak, (u / peak) ** 2, np.exp(-(u - peak) * d / 0.18))
    y *= env[:, None]
    ang = (np.linspace(-0.6 * width, 0.6 * width, n) + 1) * np.pi / 4
    y[:, 0] *= np.cos(ang) * 1.4
    y[:, 1] *= np.sin(ang) * 1.4
    return y


def blip(f0, up=True, d=0.12):
    t = tt(d)
    f = f0 * (1.5 ** (1 - np.exp(-t / 0.01)) if up else 0.6 ** (1 - np.exp(-t / 0.012)))
    x = (sine(f, d) + sine(2 * f, d) * 0.1) * np.minimum(1, t / 0.001) * np.exp(-t / 0.014)
    out = np.zeros(int((d + 0.06) * SR))
    out[:len(x)] += x
    e = int(0.055 * SR)
    out[e:e + len(x)] += x * 0.3
    return out


def riser(d=2.0, f0=250, f1=6000, midi=62):
    n = int(d * SR)
    u = np.arange(n) / SR / d
    y = sweep_filter(np.stack([noise(d), noise(d)], axis=1), f0 * (f1 / f0) ** (u ** 1.3), 'band') * (u ** 2.2)[:, None] * 0.9
    f = mtof(midi) * 2 ** (u ** 2)
    s = sweep_filter(saw_blep(f, d) * 0.5 + saw_blep(f * 1.005, d) * 0.5, 400 + 4000 * u ** 2, 'low') * (u ** 2.5) * 0.3
    return y + np.stack([s, s], axis=1)


def supersaw(midi, d, voices=5, detune=0.1, cutoff=1800, a=0.3, r=0.9):
    tot = np.zeros((int(d * SR), 2))
    for v in range(voices):
        off = (v - (voices - 1) / 2) / ((voices - 1) / 2 + 1e-9) * detune
        s = saw_blep(mtof(midi + off), d, phase0=rng.random())
        ang = ((v / (voices - 1) - 0.5) * 1.4 + 1) * np.pi / 4
        tot[:, 0] += s * np.cos(ang)
        tot[:, 1] += s * np.sin(ang)
    return filt(tot / voices, sos_lp(cutoff, 2)) * adsr(d, a, 0.3, 0.85, r)[:, None]


def felt(midi, d=1.2, bright=2600, tau=0.55):
    """Felt-piano-like pluck: soft attack, few harmonics, quick high-frequency decay."""
    t = tt(d)
    f = mtof(midi)
    x = sine(f, d) + sine(2 * f, d) * 0.35 * np.exp(-t / 0.25) + sine(3 * f, d) * 0.12 * np.exp(-t / 0.12)
    x += saw_blep(f, d) * 0.08 * np.exp(-t / 0.08)
    x = filt(x, sos_lp(bright, 1))
    hammer = filt(noise(d), sos_bp(900, 3000, 1)) * np.exp(-t / 0.004) * 0.06
    return (x * np.exp(-t / tau) + hammer) * np.minimum(1, t / 0.004)


def pluck(midi, d=0.4, c0=4200, c1=400, tau_f=0.08, tau_a=0.18):
    t = tt(d)
    f = mtof(midi)
    s = saw_blep(f, d) * 0.6 + sine(f * 2, d) * 0.1
    y = sweep_filter(s, c1 + (c0 - c1) * np.exp(-t / tau_f), 'low', 2, 128)
    return y * np.exp(-t / tau_a) * np.minimum(1, t / 0.002)


def bass(midi, d, drive=1.2, cut=700):
    f = mtof(midi)
    x = filt(sine(f, d) + sine(2 * f, d) * 0.2 + saw_blep(f, d) * 0.05, sos_lp(cut, 2))
    return sat(x, drive) * adsr(d, 0.01, 0.12, 0.8, 0.12)


# ---------------------------------------------------------------------------------------
# harmony
# ---------------------------------------------------------------------------------------
MINOR = {  # D minor: i – VI – iv – V
    'Dm': dict(pad=[50, 53, 57, 62], bass=38, arp=[62, 65, 69, 74]),
    'Bb': dict(pad=[46, 53, 58, 62], bass=34, arp=[62, 65, 70, 74]),
    'Gm': dict(pad=[43, 50, 55, 58], bass=31, arp=[62, 67, 70, 74]),
    'A': dict(pad=[45, 52, 57, 61], bass=33, arp=[61, 64, 69, 73]),
}
MAJOR = {  # D major: I – V/3 – vi – IV
    'D': dict(pad=[50, 54, 57, 62, 64], bass=38, arp=[62, 66, 69, 74]),
    'A/C#': dict(pad=[49, 52, 57, 61, 64], bass=37, arp=[61, 64, 69, 73]),
    'Bm': dict(pad=[47, 54, 59, 62, 66], bass=35, arp=[62, 66, 71, 74]),
    'G': dict(pad=[43, 50, 55, 59, 62, 66], bass=31, arp=[62, 67, 71, 74]),
    'Asus': dict(pad=[45, 52, 57, 62, 64], bass=33, arp=[62, 64, 69, 74]),
}
PROG_MINOR = {1: 'Dm', 2: 'Dm', 3: 'Dm', 4: 'Bb', 5: 'Gm', 6: 'A', 7: 'Dm', 8: 'Bb', 9: 'Gm', 10: 'A'}
# Major section starts on the light (33.0 = bar 17 beat 2); chords then change on bar lines.
PROG_MAJOR = [(M['light'], 'D'), (bar(19), 'A/C#'), (bar(20), 'Bm'), (bar(21), 'G'), (bar(22), 'D'), (bar(23), 'A/C#'),
              (bar(24), 'Bm'), (bar(25), 'G'), (bar(26), 'D'), (bar(27), 'A/C#'), (bar(28), 'G'), (bar(29), 'Asus')]
FINAL = M['tagline']
SCALE_MINOR = [62, 64, 65, 67, 69, 70, 72, 74]
SCALE_MAJOR = [62, 64, 66, 69, 71, 74, 76, 78, 81]


def build_music():
    pad, drums, bassb, arp, bells = buf(), buf(), buf(), buf(), buf()
    freeze = M['freeze']

    # --- the problem: D minor ------------------------------------------------------------
    for b_, name in PROG_MINOR.items():
        start = bar(b_)
        if start >= freeze:
            break
        d = min(BAR + 0.8, freeze - start)
        level = 0.16 + 0.03 * b_
        cut = 700 + 160 * b_
        for m in MINOR[name]['pad']:
            place(pad, supersaw(m, d, cutoff=cut, a=0.4 if b_ < 3 else 0.15, r=0.5), start, level / 4)
        if b_ >= 3:  # bass pulse on the 8ths
            for k in range(8):
                t0 = start + k * BEAT / 2
                if t0 < freeze:
                    place(bassb, bass(MINOR[name]['bass'] + (12 if k % 2 else 0), BEAT / 2 * 0.9, cut=500 + 50 * b_), t0, 0.28)
        if b_ >= 6:  # 16th ostinato, tightening: the filter opens bar by bar
            notes = MINOR[name]['arp']
            for k in range(16):
                t0 = start + k * BEAT / 4
                if t0 >= freeze:
                    break
                prog = (t0 - bar(6)) / (freeze - bar(6))
                place(arp, pluck(notes[(k * 3) % 4] + (12 if k % 8 == 7 else 0), 0.3, c0=1500 + 5200 * prog, tau_a=0.12), t0, 0.14 + 0.1 * prog, pan=0.35 if k % 2 else -0.35)

    # the clock: tick-tock on the beat from bar 1, 8ths from bar 6, 16ths in the last bar
    t0 = bar(1, 2)
    while t0 < freeze - 1e-6:
        k = int(round(t0 / (BEAT / 4)))
        on_beat = k % 4 == 0
        on_8th = k % 2 == 0
        dense = 1 if t0 < bar(6) else 2 if t0 < bar(10) else 4
        if (dense == 1 and on_beat) or (dense == 2 and on_8th) or dense == 4:
            hi = (k // 4) % 2 == 0
            place(drums, tick(3400 if hi else 2500, tau=0.005, body=0.7), t0, 0.16 if on_beat else 0.09, pan=0.25 if hi else -0.25)
        t0 += BEAT / 4
    for b_ in range(8, 11):  # soft kick joins as the load gets heavy
        for beat in range(4):
            t0 = bar(b_, beat)
            if t0 < freeze:
                place(drums, kick(0.6, 0.8), t0, 0.35 + 0.1 * (b_ - 8))
    place(pad, riser(freeze - M['overload'], midi=62), M['overload'], 0.22)

    # --- the freeze: dead stop, one low hit ----------------------------------------------
    place(bassb, sub_boom(3.5), M['harder'], 0.9)
    place(pad, supersaw(38, 2.0, cutoff=500, a=0.005, r=1.8) * 1.0, M['harder'], 0.2)
    place(bells, fm_bell(50, 4, idx=3.2, ratio=1.41, tau=1.6), M['harder'], 0.18)

    # --- abroad: dissonant drone, a slow heartbeat ----------------------------------------
    t0, t1 = M['dusk'], M['question']
    d = t1 - t0 + 0.3
    t = tt(d)
    swell = np.minimum(1, t / 2.5) * (0.6 + 0.4 * (t / d))
    drone = (sine(mtof(26), d) * 0.6 + saw_blep(mtof(39), d) * 0.05 + saw_blep(mtof(38), d) * 0.05 + sine(mtof(51), d) * 0.08) * swell
    place(pad, filt(drone, sos_lp(700, 2)), t0, 0.5)
    for m, off in ((62, 0.0), (63, 0.08), (69, 0.02)):
        place(pad, supersaw(m, d, cutoff=900, a=2.5, r=0.6), t0 + off, 0.06)
    for b_ in range(12, 16):  # heartbeat: lub-dub once a bar
        place(drums, kick(0.5, 0.6), bar(b_), 0.5)
        place(drums, kick(0.4, 0.5), bar(b_, 0.6), 0.32)
    for k, (tm, m) in enumerate([(bar(12, 2), 87), (bar(13, 3), 86), (bar(14, 2), 87), (bar(15, 1), 88)]):
        place(bells, fm_bell(m, 2.5, idx=2.8, ratio=2.76, tau=0.9), tm, 0.05, pan=0.5 if k % 2 else -0.5)
    place(pad, riser(1.6, 300, 5000, midi=63), M['can'] + 0.0, 0.16)

    # --- the question: near-silence, one thin note ---------------------------------------
    d = M['light'] - M['question']
    t = tt(d)
    thin = sine(mtof(81), d) * (0.5 + 0.5 * np.sin(2 * np.pi * 4.5 * t) ** 2) * np.minimum(1, t / 0.8) * np.exp(-t / 4)
    place(pad, thin, M['question'], 0.035)
    for k in range(4):  # the clock, slowing and fading
        place(drums, tick(2500 if k % 2 else 3400, tau=0.005), M['question'] + 0.25 + k * 0.62, 0.06 * (1 - k / 4.5))

    # --- the answer: D major ---------------------------------------------------------------
    place(pad, riser(0.7, 800, 9000, midi=74) * 0.6, M['light'] - 0.7, 0.18)
    place(bassb, sub_boom(4.0, f0=48, f1=36.7), M['light'], 0.55)
    place(bells, fm_bell(86, 4, idx=1.6, ratio=2.0, tau=1.8), M['light'], 0.12, pan=0.3)
    place(bells, fm_bell(81, 4, idx=1.6, ratio=2.0, tau=1.8), M['light'] + 0.02, 0.12, pan=-0.3)
    spans = PROG_MAJOR + [(FINAL, None)]
    for (s0, name), (s1, _) in zip(spans, spans[1:]):
        d = s1 - s0 + 0.9
        first = s0 == M['light']
        for m in MAJOR[name]['pad']:
            place(pad, supersaw(m, d, cutoff=2600 if not first else 1800, a=0.9 if first else 0.25, r=0.9), s0, 0.34 / 5)
        place(bassb, bass(MAJOR[name]['bass'], s1 - s0, drive=1.1, cut=500), s0, 0.35)
        # felt-piano arpeggio on the 8ths, gentle, from the bar after the light
        if s0 >= bar(18):
            notes = MAJOR[name]['arp']
            pattern = [0, 2, 1, 3, 2, 1, 3, 2]
            k, t0 = 0, s0
            while t0 < s1 - 1e-6:
                place(arp, felt(notes[pattern[k % 8]] + (12 if k % 8 == 3 else 0), 1.2), t0, 0.16, pan=0.3 if k % 2 else -0.3)
                t0 += BEAT / 2
                k += 1
    for b_ in range(19, 29):  # a soft pulse returns: half-time kick, shaker 8ths
        place(drums, kick(0.6, 0.7), bar(b_), 0.3)
        place(drums, kick(0.5, 0.6), bar(b_, 2.5), 0.18)
        for k in range(8):
            place(drums, hat(0.08, 0.012, 9000), bar(b_, k / 2), 0.07 if k % 2 else 0.04, pan=0.2)

    # --- the promise: final D(add9) ----------------------------------------------------------
    d = END - FINAL + 1.0
    for m in (38, 50, 54, 57, 62, 64, 69, 74):
        place(pad, supersaw(m, d, cutoff=3000, a=0.08, r=2.0), FINAL, 0.38 / 8)
    place(arp, felt(74, 3.0, tau=1.6), FINAL, 0.2)
    place(arp, felt(78, 3.0, tau=1.6), FINAL + 0.12, 0.14)
    place(bells, fm_bell(86, 5, idx=1.4, ratio=2.0, tau=2.2), FINAL + 0.02, 0.12)
    place(bassb, bass(26, d, drive=1.1, cut=400), FINAL, 0.4)

    return dict(pad=filt(pad, sos_hp(120, 2)), drums=drums, bass=bassb, arp=arp, bells=bells)


# ---------------------------------------------------------------------------------------
# sound design: one voice per cue name, consonant after the light, tense before it
# ---------------------------------------------------------------------------------------
def build_sfx():
    fx = buf()
    light = M['light']
    for c in CUES['sfx']:
        t, name, g = c['t'], c['name'], c.get('gain', 1.0)
        i = c.get('i', 0)
        major = t >= light
        scale = SCALE_MAJOR if major else SCALE_MINOR
        if name == 'word':
            place(fx, blip(mtof(scale[i % len(scale)] + 12), True, 0.1), t, 0.10)
        elif name == 'whoosh':
            place(fx, whoosh(c.get('d', 1.0), peak=0.5), t, 0.16 * g)
        elif name == 'verb':
            place(fx, tock(900 + 120 * i, 0.14), t, 0.35)
            place(fx, felt(SCALE_MINOR[i % 8], 0.8, bright=1800, tau=0.3), t, 0.2)
        elif name == 'reel':
            place(fx, tick(2600 + 90 * (c.get('k', 0) % 7), tau=0.004), t, 0.12, pan=0.3 if c.get('k', 0) % 2 else -0.3)
        elif name in ('land', 'drop'):
            k = c.get('k', i)
            place(fx, tock(420 + (k * 97) % 380, 0.12, low=0.6), t, (0.22 if name == 'land' else 0.12) * g, pan=((k * 37) % 11 - 5) / 8)
        elif name == 'tick':
            place(fx, tick(3000), t, 0.12 * g)
        elif name == 'fan':
            for k in range(4):
                place(fx, filt(noise(0.06), sos_bp(1800, 6000)) * np.exp(-tt(0.06) / 0.015), t + k * 0.05, 0.08)
        elif name == 'type':
            place(fx, key_click(int(t * 1000)), t, 0.18)
        elif name == 'click':
            place(fx, ui_click(), t, 0.3)
        elif name == 'ding':
            place(fx, blip(mtof(76 + 3 * c.get('k', 0)), True, 0.12), t, 0.12)
        elif name == 'stop':
            place(fx, tock(260, 0.2, tau=0.05, low=0.9), t, 0.45)
        elif name == 'hit':
            pass  # the music carries it
        elif name == 'dusk':
            place(fx, whoosh(1.6, 900, 200, 90, peak=0.3, air=0.02), t, 0.12)
        elif name == 'constraint':
            place(fx, sub_boom(1.6, 60, 40, 0.3), t, 0.35)
            place(fx, felt(62, 1.5, bright=1400) + felt(63, 1.5, bright=1400), t, 0.16)  # a minor second
        elif name == 'tag':
            place(fx, blip(mtof([87, 88, 86, 89][c.get('k', 0) % 4]), c.get('k', 0) % 2 == 0, 0.08), t, 0.05 * g * 2, pan=((c.get('k', 0) * 13) % 9 - 4) / 5)
        elif name == 'sting':
            place(fx, fm_bell(75, 2.5, idx=3.0, ratio=1.41, tau=1.0), t, 0.1)
        elif name == 'recede':
            place(fx, whoosh(1.4, 2000, 600, 120, peak=0.25, air=0.05), t, 0.12)
        elif name == 'bell':
            place(fx, fm_bell(81, 4, idx=1.8, ratio=3.5, tau=1.5), t, 0.16)
        elif name == 'stack':
            place(fx, tock(1400 + (i * 53) % 300, 0.08, tau=0.02, low=0.2), t, 0.1 * g)
        elif name == 'scan':
            d = c.get('d', 0.75)
            u = tt(d) / d
            x = sweep_filter(np.stack([noise(d), noise(d)], axis=1), 1200 * (6 ** u), 'band') * (np.sin(np.pi * u) ** 2)[:, None]
            place(fx, x, t, 0.05)
        elif name == 'flip':
            place(fx, whoosh(0.45, 400, 3000, 800, peak=0.5, air=0.2), t, 0.14)
            place(fx, tock(1800, 0.06, tau=0.01, low=0.1), t + 0.5, 0.12)
        elif name == 'row':
            place(fx, felt(SCALE_MAJOR[i % 9] + 12, 0.9, tau=0.4), t, 0.07 * g)
        elif name == 'met':
            place(fx, fm_bell(SCALE_MAJOR[(i + 3) % 9] + 12, 1.2, idx=1.0, ratio=2.0, tau=0.35), t, 0.07)
        elif name == 'conflict':
            place(fx, felt(50, 1.2, bright=900, tau=0.4) + felt(51, 1.2, bright=900, tau=0.4), t, 0.2)
            place(fx, tock(300, 0.14, low=0.7), t, 0.18)
        elif name == 'verify':
            place(fx, felt(69, 0.6, tau=0.25), t, 0.16)
            place(fx, felt(71, 0.9, tau=0.35), t + 0.14, 0.16)
        elif name == 'sink':
            place(fx, whoosh(0.9, 900, 400, 120, peak=0.4, air=0.02), t, 0.12)
        elif name == 'question':
            place(fx, fm_bell(76, 2.0, idx=1.2, ratio=2.0, tau=0.6), t, 0.1)
        elif name == 'rise':
            for k, m in enumerate([62, 66, 69, 74, 78, 81]):
                place(fx, felt(m + 12, 1.0, tau=0.5), t + k * BEAT / 4, 0.1)
            place(fx, riser(0.9, 1500, 9000, midi=74) * 0.5, t, 0.1)
        elif name == 'card':
            place(fx, fm_bell(81, 2.5, idx=1.2, ratio=2.0, tau=0.9), t, 0.09 * g)
        elif name == 'final':
            pass  # the music carries it
    return fx


# ---------------------------------------------------------------------------------------
# mix and master
# ---------------------------------------------------------------------------------------
def limiter(x, ceiling=0.85, look=0.004, release=0.08):
    up = signal.resample_poly(x, 4, 1, axis=0)
    a4 = np.max(np.abs(up), axis=1)
    a = a4[: (len(a4) // 4) * 4].reshape(-1, 4).max(axis=1)
    a = np.pad(a, (0, max(0, len(x) - len(a))))[: len(x)]
    la = int(look * SR)
    peak = np.maximum.reduce([np.roll(a, -k) for k in range(0, la, 8)])
    gain = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    win = np.hanning(max(3, la))
    gain = np.minimum(gain, np.convolve(gain, win / win.sum(), mode='same'))
    rel = np.exp(-1 / (release * SR))
    out = np.empty_like(gain)
    g = 1.0
    for i in range(len(gain)):
        g = gain[i] if gain[i] < g else gain[i] + (g - gain[i]) * rel
        out[i] = g
    return x * out[:, None]


def main():
    m = build_music()
    fx = build_sfx()
    t = np.arange(N) / SR
    freeze, harder = M['freeze'], M['harder']

    music = m['pad'] * 1.5 + m['drums'] * 0.8 + m['bass'] * 0.7 + m['arp'] * 1.4 + m['bells'] * 1.3
    send = filt(m['pad'] * 0.3 + m['arp'] * 0.45 + m['bells'] * 0.7 + m['drums'] * 0.05 + fx * 0.25, sos_hp(250, 2))
    wet = reverb(send, IR_HALL)

    # The freeze: a dead stop — every sound, tails included, cut on the beat until the hit.
    hold = np.ones(N)
    w = (t >= freeze) & (t < harder - 0.005)
    hold[w] = 0.0
    ramp = int(0.012 * SR)
    i0 = int(freeze * SR)
    hold[i0 - ramp:i0] = np.linspace(1, 0, ramp)
    hold = hold[:, None]

    mix = (music + wet * 0.55 + fx * 1.1) * hold
    mix = filt(mix, sos_hp(28, 2))
    mid = mix.mean(axis=1, keepdims=True)  # mono below 120 Hz
    side = filt((mix[:, :1] - mix[:, 1:]) / 2, sos_hp(120, 2))
    mix = np.concatenate([mid + side, mid - side], axis=1)
    mix = sat(mix * 0.9, 1.1)

    fade = np.clip((END - 0.02 - t) / 1.6, 0, 1) ** 2  # rings out over the lockup, silent at the end
    mix *= fade[:, None]

    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    body = slice(0, int((END - 1.0) * SR))
    for _ in range(3):
        lufs = meter.integrated_loudness(mix[body])
        mix *= 10 ** ((-16.0 - lufs) / 20)  # a presentation room, not a feed: -16 LUFS
        mix = limiter(mix, ceiling=0.8)
    mix = mix[: int(END * SR)]

    import soundfile as sf
    out = os.path.join(ROOT, 'audio', 'soundtrack.wav')
    sf.write(out, mix.astype(np.float32), SR, subtype='PCM_24')
    print(f'wrote audio/soundtrack.wav {len(mix) / SR:.2f}s, {meter.integrated_loudness(mix[body]):.1f} LUFS, peak {np.max(np.abs(mix)):.2f}')


if __name__ == '__main__':
    main()
