#!/usr/bin/env python3
"""Applicable.ai launch film - score and sound design, synthesized from scratch.

Reads out/cues.json (exported from the same timeline and motion functions the picture uses) and
writes public/audio/soundtrack.wav (48 kHz, 24-bit stereo) plus stems in out/stems/.
No samples, no loops, no downloaded sounds: oscillators, noise, filters, convolution.
Deterministic (seeded): re-running reproduces the exact mix.

Sonic identity
  * Time: a clock that is not a clock - one dry wooden tick per beat while the posting ages,
    rising a step each time its age label changes.
  * Competition: every applicant is a click (99 of them, on the frames their seats fill); together
    they thicken into a crowd murmur that peaks on "100+".
  * The problem world is D minor, unstable (drifting, detuned pads, a pulse that pushes).
  * Detection: the "edge ping", an FM bell figure A - D - F# (rising 4th, major 3rd). It sounds when
    Applicable.ai appears, when a fresh role is born at the edge, when the new role lands at #1
    and on the final lockup.
  * Resolution: the same root turns major (D minor -> D major) when Applicable.ai appears, and the
    film ends on D add9 with the clock ticking calmly, in time.

Usage: python3 scripts/soundtrack.py
"""
import json
import os

import numpy as np
from scipy import signal

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUES = json.load(open(os.path.join(ROOT, 'out', 'cues.json')))
FPS = CUES['fps']
END = CUES['total'] / FPS  # 30.000 s
DUR = END + 1.5  # render a tail, trimmed at the end
N = int(DUR * SR)
BEAT = 60.0 / CUES['bpm']
BAR = 4 * BEAT
rng = np.random.default_rng(20260929)

C = CUES['cue']
A1, A2, A3, A4, A5, A6 = (CUES[k] for k in ('act1', 'act2', 'act3', 'act4', 'act5', 'act6'))
WORDS = CUES['words']


def fr(frame):
    return frame / FPS


def bar(n, beat=0.0):
    """1-indexed bar + beat -> seconds"""
    return (n - 1) * BAR + beat * BEAT


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------------------------------------
# buffers and DSP
# ------------------------------------------------------------------------------------------------
def buf():
    return np.zeros((N, 2))


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(dst, x, t, gain=1.0, pan=0.0):
    """Mix mono/stereo x into dst at time t (s), constant-power pan, with a short tail fade."""
    i = int(round(t * SR))
    if i >= N or len(x) == 0:
        return
    if x.ndim == 1:
        a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        x = np.stack([x * np.cos(a), x * np.sin(a)], axis=1)
    x = x.copy()
    nf = min(len(x), int(0.005 * SR))
    x[-nf:] *= (np.cos(np.linspace(0, np.pi / 2, nf)) ** 2)[:, None]
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), N - i)
    dst[i:i + n] += x[:n] * gain


def place_peak(dst, x, frac, t_peak, gain=1.0, pan=0.0):
    """Place a swell so its apex (at `frac` of its length) lands on t_peak."""
    place(dst, x, t_peak - frac * len(x) / SR, gain, pan)


def sos(kind, f, order=2):
    if kind == 'band':
        return signal.butter(order, [max(f[0], 10), min(f[1], SR * 0.45)], 'band', fs=SR, output='sos')
    return signal.butter(order, min(max(f, 10), SR * 0.45), kind, fs=SR, output='sos')


def filt(x, s):
    return signal.sosfilt(s, x, axis=0)


def sweep(x, cut, kind='low', block=256, order=2):
    """Time-varying Butterworth, cutoff per sample (processed in blocks with carried state)."""
    y = np.zeros_like(x)
    zi = None
    for s0 in range(0, len(x), block):
        c = float(np.mean(cut[s0:s0 + block]))
        s = sos('band', (c / 1.4, c * 1.4), order) if kind == 'band' else sos(kind, c, order)
        if zi is None:
            zi = np.zeros((s.shape[0], 2) + x.shape[1:])
        y[s0:s0 + block], zi = signal.sosfilt(s, x[s0:s0 + block], axis=0, zi=zi)
    return y


def noise(d):
    return rng.standard_normal(int(d * SR))


def sine(f, d, ph=0.0):
    n = int(d * SR)
    f = np.full(n, f) if np.isscalar(f) else f[:n]
    return np.sin(2 * np.pi * (ph + np.cumsum(f) / SR))


def saw(f, d, ph=0.0):
    """PolyBLEP band-limited saw (scalar or per-sample frequency)."""
    n = int(d * SR)
    f = np.full(n, f) if np.isscalar(f) else f[:n]
    dt = f / SR
    p = (ph + np.cumsum(dt)) % 1.0
    y = 2 * p - 1
    m = p < dt
    t = p[m] / dt[m]
    y[m] -= t + t - t * t - 1
    m = p > 1 - dt
    t = (p[m] - 1) / dt[m]
    y[m] -= t * t + t + t + 1
    return y


def env_adsr(d, a=0.01, dc=0.2, s=0.7, r=0.3):
    n = int(d * SR)
    e = np.full(n, s)
    na, nd, nr = max(1, int(a * SR)), int(dc * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na)
    if na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd)
    if 0 < nr < n:
        e[-nr:] *= np.linspace(1, 0, nr) ** 1.6
    return e


def sat(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


def make_ir(rt60, pre, lp, width, seed):
    r = np.random.default_rng(seed)
    n = int(rt60 * 1.3 * SR)
    t = np.arange(n) / SR
    ir = np.stack([r.standard_normal(n), r.standard_normal(n)], axis=1) * np.exp(-6.9 * t / rt60)[:, None]
    ir = filt(ir, sos('low', lp, 1))
    mid = ir.mean(axis=1, keepdims=True)
    ir = mid + (ir - mid) * width
    ir = np.concatenate([np.zeros((int(pre * SR), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2))


IR_HALL = make_ir(2.6, 0.022, 6000, 1.0, 3)
IR_ROOM = make_ir(0.6, 0.006, 7500, 0.8, 5)
IR_DARK = make_ir(3.4, 0.03, 2600, 1.0, 9)


def reverb(x, ir):
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    return np.stack([signal.fftconvolve(x[:, k], ir[:, k])[:len(x)] for k in (0, 1)], axis=1)


# ------------------------------------------------------------------------------------------------
# instruments
# ------------------------------------------------------------------------------------------------
def kick(hard=1.0, d=0.8):
    t = tt(d)
    f = mtof(26) + 120 * np.exp(-t / 0.03) + 60 * np.exp(-t / 0.005)  # settles on D1: in key
    body = sine(f, d) * np.exp(-t / (0.22 * hard + 0.05))
    click = filt(noise(d), sos('high', 3000)) * np.exp(-t / 0.002) * 0.3
    return sat(body * 1.1 + click, 1.7) * 0.9


def sub_boom(f0=73.4, f1=36.7, d=2.6, glide=0.1):
    t = tt(d)
    f = f1 + (f0 - f1) * np.exp(-t / glide)
    x = sine(f, d) * np.exp(-t / 0.95) + sine(2 * f, d) * np.exp(-t / 0.22) * 0.22
    thump = filt(noise(d), sos('low', 170)) * np.exp(-t / 0.045) * 0.6
    return sat(x, 1.3) * 0.9 + thump


def clap(d=0.4):
    t = tt(d)
    n = filt(noise(d), sos('band', (1000, 5000)))
    e = sum((t >= o) * np.exp(-np.maximum(t - o, 0) / (0.005 if k < 3 else 0.09)) for k, o in enumerate((0, 0.008, 0.017, 0.026)))
    return n * e * 0.8


def shaker(d=0.09, bright=6500):
    t = tt(d)
    return filt(noise(d), sos('high', bright)) * (np.minimum(1, t / 0.006) * np.exp(-t / 0.025)) * 0.5


def hat(d=0.1, tau=0.02):
    t = tt(d)
    ring = sum(np.sin(2 * np.pi * f * t) for f in (7900, 10700, 13100)) * 0.07
    return (filt(noise(d), sos('high', 7500)) + ring) * np.exp(-t / tau) * 0.5


def wood(freq, d=0.12, tau=0.025, low=0.3):
    """A wooden tick: an excited resonant band plus a small low thump."""
    t = tt(d)
    exc = noise(d) * np.exp(-t / 0.0035)
    res = filt(exc, sos('band', (freq * 0.9, freq * 1.12))) * 7 * np.exp(-t / tau)
    return res + np.sin(2 * np.pi * freq / 8 * t) * np.exp(-t / 0.02) * low


def click(seed, bright=1.0):
    """One applicant: a short, slightly pitched click (each one different)."""
    r = np.random.default_rng(seed)
    d = 0.04
    t = tt(d)
    f = 1800 + r.random() * 2600 * bright
    x = filt(noise(d), sos('band', (f * 0.75, f * 1.3))) * np.exp(-t / (0.0025 + r.random() * 0.003))
    x += np.sin(2 * np.pi * (220 + r.random() * 160) * t) * np.exp(-t / 0.008) * 0.2
    return x * (0.6 + 0.4 * r.random())


def fm_bell(midi, d=2.5, idx=2.0, ratio=3.5, tau=1.1, att=0.002):
    d = max(d, 4 * tau)
    t = tt(d)
    fc = mtof(midi)
    mod = np.sin(2 * np.pi * fc * ratio * t) * idx * np.exp(-t / 0.3)
    x = np.sin(2 * np.pi * fc * t + mod) * np.exp(-t / tau)
    x += np.sin(2 * np.pi * fc * 2 * t) * np.exp(-t / (tau * 0.3)) * 0.12
    return x * np.minimum(1, t / att)


def epiano(midi, d=1.2, vel=1.0):
    """Warm FM electric piano (1:1 carrier/modulator with a decaying index and a tine partial)."""
    t = tt(d)
    fc = mtof(midi)
    idx = (1.2 + 1.4 * vel) * np.exp(-t / 0.18)
    x = np.sin(2 * np.pi * fc * t + idx * np.sin(2 * np.pi * fc * t))
    x += np.sin(2 * np.pi * fc * 14 * t) * np.exp(-t / 0.012) * 0.05 * vel
    return x * np.exp(-t / 0.9) * np.minimum(1, t / 0.003)


def pad_note(midi, d, cut=1600, detune=0.08, voices=3, drift=0.0, a=0.3, r=0.9):
    tot = np.zeros((int(d * SR), 2))
    t = tt(d)
    for v in range(voices):
        off = (v - (voices - 1) / 2) * detune
        wob = drift * np.sin(2 * np.pi * (0.13 + 0.05 * v) * t + v) if drift else 0
        f = mtof(midi + off + wob)
        s = saw(f, d, ph=rng.random())
        pan = (v / max(1, voices - 1) - 0.5) * 1.2
        ang = (pan + 1) * np.pi / 4
        tot[:, 0] += s * np.cos(ang)
        tot[:, 1] += s * np.sin(ang)
    tot = filt(tot / voices, sos('low', cut, 2))
    return tot * env_adsr(d, a, 0.4, 0.85, r)[:, None]


def bass_note(midi, d, drive=1.3, bright=900):
    f = mtof(midi)
    x = sine(f, d) + sine(2 * f, d) * 0.25 + saw(f, d) * 0.07
    return sat(filt(x, sos('low', bright)), drive) * env_adsr(d, 0.005, 0.1, 0.8, 0.06)


def whoosh(d=0.7, f0=200, f1=1600, f2=300, peak=0.5, width=0.8, air=0.1):
    n = int(d * SR)
    u = np.arange(n) / n
    cut = np.where(u < peak, f0 * (f1 / f0) ** (u / peak), f1 * (f2 / f1) ** ((u - peak) / (1 - peak)))
    def colored():
        w = noise(d)
        b = filt(np.cumsum(w), sos('high', 30))
        b /= np.max(np.abs(b)) + 1e-9
        return b * 0.7 + filt(w, sos('low', 4000, 1)) * 0.3
    x = np.stack([colored(), colored()], axis=1)
    y = sweep(x, cut, 'band') * 2.2 + filt(np.stack([noise(d), noise(d)], axis=1), sos('high', 4000)) * air
    e = np.where(u < peak, (u / peak) ** 2, np.exp(-(u - peak) * d / 0.16))
    y *= e[:, None]
    pan = np.linspace(-0.6, 0.6, n) * width
    y[:, 0] *= np.cos((pan + 1) * np.pi / 4) * 1.4
    y[:, 1] *= np.sin((pan + 1) * np.pi / 4) * 1.4
    return y


def riser(d=2.0, f0=250, f1=7000, midi=57, tone=0.3):
    n = int(d * SR)
    u = np.arange(n) / n
    x = sweep(np.stack([noise(d), noise(d)], axis=1), f0 * (f1 / f0) ** (u ** 1.3), 'band') * (u ** 2.2)[:, None]
    if tone:
        f = mtof(midi) * 2 ** (u ** 2)
        s = sweep((saw(f, d) + saw(f * 1.006, d)) * 0.5, 400 + 5000 * u ** 2, 'low') * u ** 2.5 * tone
        x += np.stack([s, s], axis=1)
    return x


def snap(root, d=0.6, weight=1.0):
    """Tile landing: a tight click, a body and a tuned low tail on the root under it."""
    t = tt(d)
    c = filt(noise(d), sos('band', (1800, 9000))) * np.exp(-t / 0.003) * 1.1
    body = sine(4 * root * (1 + 0.6 * np.exp(-t / 0.008)), d) * np.exp(-t / 0.04) * 0.6
    low = sine(root * (1 + 0.4 * np.exp(-t / 0.02)), d) * np.exp(-t / 0.18) * weight
    return sat(c + body + low, 1.3)


def sink(d=0.5, f0=420):
    """An old role sinking back: a soft low tone falling a fifth, through a closing filter."""
    t = tt(d)
    f = f0 * (2 / 3) ** np.minimum(1, t / 0.35)
    x = sine(f, d) * 0.7 + saw(f, d) * 0.12
    return filt(x, sos('low', 900)) * np.minimum(1, t / 0.01) * np.exp(-t / 0.16)


def murmur(d, amt):
    """The crowd: band-limited noise with a restless, many-voiced amplitude flutter."""
    n = int(d * SR)
    x = filt(np.stack([noise(d), noise(d)], axis=1), sos('band', (260, 2400)))
    fl = filt(rng.standard_normal((n, 2)), sos('low', 9)) * 3.0
    x *= (1 + np.clip(fl, -1, 1) * 0.6)
    return x * amt[:n, None]


# ------------------------------------------------------------------------------------------------
# harmony: D minor (the problem) -> D major (Applicable.ai)
# ------------------------------------------------------------------------------------------------
CH = {
    'Dm': [50, 57, 62, 65, 69], 'Dm9': [50, 57, 64, 65, 69], 'Gm/D': [50, 55, 62, 67, 70],
    'Bbmaj7#11': [46, 53, 57, 62, 64], 'A7sus': [45, 52, 55, 62, 64],
    'Dmaj9': [50, 57, 64, 66, 69, 73], 'Gmaj7/D': [50, 55, 62, 66, 71],
    'D': [50, 57, 62, 66, 69], 'Bm7': [47, 54, 57, 62, 66], 'Gmaj7': [43, 50, 59, 62, 66],
    'A': [45, 52, 57, 61, 64], 'G': [43, 50, 55, 62, 67, 71], 'Asus': [45, 52, 57, 62, 64],
    'Dadd9': [50, 57, 62, 64, 66, 69, 76],
}
ROOTS = {'Dm': 38, 'Dm9': 38, 'Gm/D': 38, 'Bbmaj7#11': 34, 'A7sus': 33, 'Dmaj9': 38, 'Gmaj7/D': 38,
         'D': 38, 'Bm7': 35, 'Gmaj7': 31, 'A': 33, 'G': 31, 'Asus': 33, 'Dadd9': 38}
EDGE = [69, 74, 78]  # the edge ping: A5 D6 F#6
D_HZ = mtof(38)


def edge_ping(dst, t, gain=0.1, scale=1.0, step=0.075, notes=EDGE, pan=0.0, tau=1.1):
    for k, m in enumerate(notes):
        place(dst, fm_bell(m, 2.5, 1.6 * scale, 3.5, tau), t + k * step, gain * (1 - 0.12 * k), pan + (k - 1) * 0.18)


# ------------------------------------------------------------------------------------------------
# music
# ------------------------------------------------------------------------------------------------
def build_music():
    drums, bass, pad, keys, bells = buf(), buf(), buf(), buf(), buf()
    kicks = []

    def K(t, g=1.0, hard=1.0):
        place(drums, kick(hard), t, g)
        kicks.append((t, g))

    # --- ACT 1: a dark D pedal that tightens toward "100+", then air ------------------------------
    t_h = fr(A1['hundred'])
    d = t_h
    t = tt(d)
    drone = (sine(mtof(38), d) * 0.6 + saw(mtof(50), d) * 0.05 + saw(mtof(57) * 1.003, d) * 0.035)
    drone = filt(drone, sos('low', 420)) * np.minimum(1, t / 1.2)
    place(pad, drone, 0.0, 0.2)
    # the tension cluster (D-Eb-A) swelling into the hit, stopping dead on it
    for m, g in ((62, 1.0), (63, 0.7), (69, 0.6)):
        x = pad_note(m, d, cut=900, detune=0.14, drift=0.08, a=d * 0.9, r=0.02)
        place(pad, x * (np.linspace(0, 1, len(x)) ** 2.2)[:, None], 0.0, 0.07 * g)
    # after the hit: a low, hollow Gm/D under the two lines, falling into the market
    for m in CH['Gm/D']:
        place(pad, pad_note(m - 12 if m > 60 else m, fr(ACT_FROM('problem')) - t_h + 0.3, cut=700, detune=0.1, drift=0.05, a=0.6, r=0.4), t_h + 0.25, 0.05)

    # --- ACT 2: overload - D minor that will not settle, a pushing pulse --------------------------
    a2 = fr(ACT_FROM('problem'))
    rv = fr(ACT_FROM('reveal'))
    prog2 = [('Dm9', a2, a2 + BAR), ('Bbmaj7#11', a2 + BAR, a2 + BAR * 1.5), ('A7sus', a2 + BAR * 1.5, rv - BEAT * 0.5)]
    for name, s0, s1 in prog2:
        for m in CH[name]:
            place(pad, pad_note(m, s1 - s0 + 0.35, cut=1300, detune=0.16, drift=0.12, a=0.18, r=0.3), s0, 0.055)
    # the pulse: 16th-note bass on the root, accents pushing ahead of the beat
    for k in range(int((rv - BEAT * 0.5 - a2) / (BEAT / 4))):
        tk = a2 + k * BEAT / 4
        name = [p for p in prog2 if p[1] <= tk < p[2]]
        if not name:
            continue
        root = ROOTS[name[0][0]]
        acc = 1.0 if k % 4 == 0 else (0.75 if k % 4 == 3 else 0.5)
        place(bass, bass_note(root + (12 if k % 8 == 6 else 0), BEAT / 4 * 0.8, 1.5, 700), tk, 0.23 * acc)
    for k in range(8):
        tk = a2 + k * BEAT
        if tk < rv - BEAT:
            K(tk, 0.75 if k % 2 == 0 else 0.5, 0.9)
            place(drums, hat(0.06, 0.012), tk + BEAT / 2, 0.08, pan=0.25)
            place(drums, hat(0.05, 0.01), tk + 3 * BEAT / 4, 0.05, pan=-0.2)
    # silence before the drop: everything above stops half a beat early

    # --- ACT 3: the reveal - D major blooms ---------------------------------------------------------
    for m in CH['Dmaj9']:
        place(pad, pad_note(m, BAR * 1.5 + 0.8, cut=2600, detune=0.06, a=0.05, r=1.0), rv, 0.07)
    for m in CH['Gmaj7/D']:
        place(pad, pad_note(m, BAR * 0.5 + 0.8, cut=2200, detune=0.06, a=0.3, r=0.9), rv + BAR * 1.5, 0.055)
    place(bass, bass_note(38, BAR * 2 - 0.1, 1.1, 500), rv, 0.3)
    # deliberate quarter-note pulse after the lockup (controlled, not pushing)
    for k in range(4, 8):
        place(keys, epiano(62 if k % 2 else 57, 0.8, 0.6), rv + k * BEAT, 0.07, pan=(-0.3 if k % 2 else 0.3))

    # --- ACT 4: freshness - a light groove in D major ------------------------------------------------
    a4 = fr(ACT_FROM('fresh'))
    a5 = fr(ACT_FROM('actFirst'))
    prog4 = [('D', a4), ('Bm7', a4 + BAR), ('Gmaj7', a4 + 2 * BAR)]
    for name, s0 in prog4:
        for m in CH[name]:
            place(pad, pad_note(m, BAR + 0.6, cut=2000, detune=0.05, a=0.25, r=0.7), s0, 0.045)
        root = ROOTS[name]
        for q in (0, 1.5, 2, 3.5):
            place(bass, bass_note(root, BEAT * (1.4 if q in (0, 2) else 0.45)), s0 + q * BEAT, 0.25 if q in (0, 2) else 0.17)
        # the arpeggio: e-piano 8ths through the chord's upper voices
        up = CH[name][1:]
        for k in range(8):
            m = up[[0, 2, 1, 3, 2, 1, 3, 2][k] % len(up)] + 12
            place(keys, epiano(m, 0.9, 0.7 if k % 2 == 0 else 0.5), s0 + k * BEAT / 2, 0.05 if k % 2 else 0.065, pan=(0.3 if k % 2 else -0.3))
        for q in range(4):
            K(s0 + q * BEAT, 0.62 if q in (0, 2) else 0.35, 0.8)
            for s in range(2):
                place(drums, shaker(), s0 + q * BEAT + s * BEAT / 2 + BEAT / 4, 0.09 if s else 0.06, pan=0.3)
        place(drums, clap(0.35), s0 + BEAT, 0.16)
        place(drums, clap(0.35), s0 + 3 * BEAT, 0.18)

    # --- ACT 5: build on the dominant, then drop 2 on the landing ---------------------------------------
    land = fr(A5['land'])
    for m in CH['Asus']:
        place(pad, pad_note(m, land - a5 - BEAT * 0.25, cut=2400, detune=0.07, a=0.2, r=0.05), a5, 0.05)
    for k in range(int((land - a5) / (BEAT / 2))):
        tk = a5 + k * BEAT / 2
        if tk < land - BEAT * 0.25:
            place(bass, bass_note(33, BEAT / 2 * 0.8, 1.4), tk, 0.16 + 0.1 * k / 8)
            place(keys, epiano(76 if k % 2 else 69, 0.6, 0.6), tk, 0.04 + 0.02 * k / 8, pan=(0.25 if k % 2 else -0.25))
    # the last bar of the build: a kick pulse doubling up, so the pressure rises into the landing
    b0 = land - BAR
    for k in range(8):
        K(b0 + k * BEAT / 2, 0.35 + 0.4 * k / 7, 0.8)
    for k in range(8):
        K(b0 + BAR / 2 + k * BEAT / 4, 0.3 + 0.3 * k / 7, 0.7) if k % 2 else None
    # snare-ish roll into the drop (claps accelerating), then a half-beat of air
    for k, tk in enumerate(np.cumsum([BEAT / 2] * 4 + [BEAT / 4] * 4 + [BEAT / 8] * 6)):
        tr = fr(A5['lift']) - 1.0 + tk * 0.9
        if tr < land - 0.07:
            place(drums, clap(0.2), tr, 0.08 + 0.16 * k / 14, pan=(k % 2 - 0.5) * 0.3)
    # drop 2: the biggest moment - four on the floor, D major wide open, octave bass
    end5 = fr(ACT_FROM('edge')) + BEAT * 2
    prog5 = [('D', land, land + BAR), ('Bm7', land + BAR, end5)]
    for name, s0, s1 in prog5:
        for m in CH[name] + [CH[name][2] + 12]:
            place(pad, pad_note(m, s1 - s0 + 0.5, cut=3600, detune=0.09, voices=4, a=0.02, r=0.6), s0, 0.06)
        root = ROOTS[name]
        for k in range(int((s1 - s0) / (BEAT / 2))):
            place(bass, bass_note(root + (12 if k % 2 else 0), BEAT / 2 * 0.85, 1.5, 1100), s0 + k * BEAT / 2, 0.3 if k % 2 == 0 else 0.22)
        for q in range(int((s1 - s0) / BEAT)):
            K(s0 + q * BEAT, 1.0 if q % 2 == 0 else 0.85)
            place(drums, hat(0.18, 0.05), s0 + q * BEAT + BEAT / 2, 0.14, pan=0.2)
            if q % 2 == 1:
                place(drums, clap(0.4), s0 + q * BEAT, 0.3)
        up = CH[name][1:] + [CH[name][2] + 12]
        for k in range(int((s1 - s0) / (BEAT / 4))):
            m = up[[0, 2, 4, 1, 3, 2, 4, 1][k % 8] % len(up)] + 12
            place(keys, epiano(m, 0.5, 0.9 if k % 4 == 0 else 0.6), s0 + k * BEAT / 4, 0.05 if k % 4 else 0.07, pan=((k % 4) - 1.5) / 4)

    # --- ACT 6: resolution - IV, the suspended V, and home -------------------------------------------
    lock = fr(A6['lockup'])
    prog6 = [('G', end5, lock - BAR * 0.5), ('Asus', lock - BAR * 0.5, lock)]
    for name, s0, s1 in prog6:
        for m in CH[name]:
            place(pad, pad_note(m, s1 - s0 + 0.4, cut=2600, detune=0.06, a=0.25, r=0.4), s0, 0.055)
        place(bass, bass_note(ROOTS[name], s1 - s0 - 0.05, 1.1, 600), s0, 0.26)
    for k in range(int((lock - end5) / BEAT)):
        place(drums, shaker(0.1, 7000), end5 + k * BEAT + BEAT / 2, 0.06, pan=0.3)
        place(keys, epiano(CH['G'][3 + k % 2] + 12 if end5 + k * BEAT < lock - BAR / 2 else 76 + (k % 2) * -2, 0.9, 0.5), end5 + k * BEAT, 0.045)
    # home: D add9 rings out under the lockup
    ring = END - lock + 1.2
    for m in CH['Dadd9']:
        place(pad, pad_note(m, ring, cut=3000, detune=0.05, voices=4, a=0.03, r=1.3), lock, 0.06)
    place(bass, bass_note(38, ring - 0.2, 1.1, 500) * np.linspace(1, 0.4, int((ring - 0.2) * SR)), lock, 0.32)
    K(lock, 1.0, 1.1)

    return dict(drums=drums, bass=bass, pad=pad, keys=keys, bells=bells, kicks=kicks)


def ACT_FROM(k):
    return CUES['acts'][k]['from']


# ------------------------------------------------------------------------------------------------
# sound design, placed on picture events
# ------------------------------------------------------------------------------------------------
def build_sfx(bells):
    fx = buf()

    # ACT 1 - the clock: a dry tick on every beat; each age step lands a step higher
    ticks = [0] + A1['ageTicks']
    for i, f in enumerate(ticks):
        g = 0.18 + 0.05 * (i / len(ticks))
        place(fx, wood(mtof(81 + [0, 2, 3, 5, 7, 8, 10][min(i, 6)]), 0.12, 0.022, 0.25), fr(f), g, pan=0.1)
    for k in range(1, 12):  # the off-beats: the clock's second hand, quieter
        tk = k * BEAT / 2
        if tk < fr(A1['hundred']) - 0.05 and k % 2:
            place(fx, wood(mtof(88), 0.05, 0.008, 0.0), tk, 0.05 + 0.03 * k / 12, pan=-0.2)
    # applicants: one click each, on the frame its seat fills, level rising with the crowd
    for n, f in enumerate(A1['applicants']):
        r = np.random.default_rng(500 + n)
        place(fx, click(700 + n), fr(f), 0.05 + 0.1 * (n / 99), pan=(r.random() - 0.5) * 1.3)
    # the crowd murmur grows with the count and breaks off on 100+ (its reverb keeps a trace)
    t = np.arange(N) / SR
    th = fr(A1['hundred'])
    amt = np.clip(t / th, 0, 1) ** 2.2 * (t < th) + (t >= th) * np.exp(-np.maximum(t - th, 0) / 0.5) * 0.35
    fx += murmur(DUR, amt * 0.06)
    place(fx, riser(th - 0.9, 300, 6000, 62, 0.25), 0.9, 0.1)
    # 100+: the hit
    place(fx, sub_boom(mtof(38) * 2, mtof(26), 2.4, 0.08), th, 0.7)
    place(fx, clap(0.5), th, 0.35)
    place(fx, filt(noise(0.7), sos('band', (180, 3200))) * np.exp(-tt(0.7) / 0.13), th, 0.25)
    for m in (50, 51, 57, 62, 63):  # a dissonant stab (D Eb A): too many people
        place(fx, pad_note(m, 1.2, cut=2400, detune=0.2, a=0.004, r=1.0) * np.exp(-tt(1.2) / 0.35)[:, None], th, 0.06)
    for k, f in enumerate(A1['spill']):
        place(fx, click(900 + k, 0.6), fr(f) + 0.02, 0.05, pan=0.4)
    place_peak(fx, whoosh(0.35, 400, 3200, 900, 0.5, 0.3), 0.5, fr(A1['punchIn']), 0.12)
    place_peak(fx, whoosh(0.7, 1200, 600, 200, 0.4, 0.5), 0.4, fr(A1['punchOut']), 0.1)
    # you: the cursor arrives and saves it
    place_peak(fx, whoosh(0.3, 1500, 4000, 2000, 0.5, 0.2, 0.05), 0.5, fr(A1['cursor']), 0.035, pan=0.4)
    tc = tt(0.15)
    ui = filt(noise(0.15), sos('high', 3000)) * np.exp(-tc / 0.0012) + np.sin(2 * np.pi * 1760 * tc) * np.exp(-tc / 0.02) * 0.3
    place(fx, ui, fr(A1['click']), 0.3, pan=0.1)
    # the two lines: a quiet note for "found it", a low hollow answer for "everyone else"
    place(bells, fm_bell(74, 2.5, 1.0, 2.0, 0.9), fr(WORDS['foundIt'][0]), 0.08)
    for i, f in enumerate(WORDS['everyone']):
        place(fx, wood(mtof([50, 50, 53, 50][i % 4]) * 2, 0.2, 0.06, 0.6), fr(f), 0.1, pan=(i - 1.5) / 5)
    # the page falls away into the market
    place_peak(fx, whoosh(1.0, 2500, 700, 150, 0.8, 0.8), 0.8, fr(A1['pullBack']), 0.2)

    # ACT 2 - the market: every posting that slides out from behind the now edge ticks, panned by lane
    for i, b in enumerate(A2['births']):
        place(fx, wood(mtof(86 + (i * 5) % 7), 0.06, 0.01, 0.0), fr(b['f']), 0.07, pan=b['pan'])
    for f in WORDS['finding'] + WORDS['notEnough']:
        place(fx, filt(noise(0.05), sos('band', (500, 1600))) * np.exp(-tt(0.05) / 0.012), fr(f), 0.05)
    # "Timing is the edge.": the pulse drops out for the word "edge"; a high tone holds the edge
    th2 = fr(A2['edgeGlow'])
    place(bells, fm_bell(81, 3.0, 0.4, 2.0, 1.4, att=0.08), th2, 0.05)
    rv = fr(A3['drop'])
    place(fx, riser(rv - th2 - 0.05, 200, 9000, 57, 0.35), th2, 0.24)
    place_peak(fx, whoosh(0.9, 200, 2200, 500, 0.85, 0.8), 0.85, fr(A2['rushPeak']), 0.26)

    # ACT 3 - the reveal
    place(fx, sub_boom(D_HZ * 2, D_HZ, 3.0, 0.12), rv, 0.8)
    place(fx, snap(D_HZ * 2, 0.8, 0.9), rv, 0.35)
    place_peak(fx, whoosh(0.8, 3000, 900, 200, 0.2, 1.0, 0.15), 0.2, fr(A3['wavePeak']), 0.22)
    place_peak(fx, whoosh(0.45, 200, 1600, 700, 0.7, 0.3), 0.7, fr(A3['collapsePeak']), 0.14)
    place(fx, snap(D_HZ * 2, 0.6, 0.8), fr(A3['tileLand']), 0.45)
    edge_ping(bells, fr(A3['aIn']), 0.13, 1.0)
    place_peak(fx, whoosh(0.4, 500, 3000, 1000, 0.4, 0.5), 0.4, fr(A3['lockShift']), 0.08)
    place_peak(fx, whoosh(0.35, 2500, 700, 300, 0.7, 0.4), 0.7, fr(A3['tuck']), 0.07)
    place_peak(fx, whoosh(0.5, 300, 2400, 600, 0.6, 0.6), 0.6, fr(A3['unfoldPeak']), 0.12)

    # ACT 4 - freshness: old roles sink (falling), fresh ones are born with the edge ping
    place_peak(fx, whoosh(0.6, 300, 1800, 400, 0.4, 0.8), 0.4, fr(A4['edgeSlide']), 0.1)
    for i, u in enumerate(sorted(A4['unfold'], key=lambda u: u['f'])):
        place(fx, wood(mtof(74 + i * 2), 0.08, 0.015, 0.0), fr(u['f']), 0.05, pan=-0.5 + 0.1 * i)
    for i, r in enumerate(A4['recede']):
        place(fx, sink(0.6, mtof(62 - i * 2)), fr(r['f']), 0.1, pan=-0.6 + 0.12 * i)
    for i, e in enumerate(A4['emerge']):
        place(fx, wood(mtof(93), 0.05, 0.01, 0.0), fr(e['f']), 0.1, pan=0.55)
        place(bells, fm_bell(EDGE[i % 3] + (12 if i == 2 else 0), 2.0, 1.4, 3.5, 0.9), fr(e['f']), 0.1, pan=0.5)
        place(fx, snap(mtof(62), 0.25, 0.3), fr(e['land']), 0.1, pan=0.35)
    place_peak(fx, whoosh(0.6, 200, 1500, 500, 0.9, 0.6), 0.9, fr(A4['push']), 0.14)

    # ACT 5 - act first
    edge_ping(bells, fr(A5['emerge']), 0.12, 1.2, pan=0.4)
    place(fx, snap(mtof(45), 0.4, 0.6), fr(A5['emergeLand']), 0.2, pan=0.35)
    for i, f in enumerate(A5['checks']):  # confirmations: two rising blips
        tc = tt(0.2)
        fq = mtof([81, 86][i]) * (1 + 0.5 * (1 - np.exp(-tc / 0.01)))
        place(fx, sine(fq, 0.2) * np.exp(-tc / 0.05), fr(f) + 0.02, 0.07, pan=0.35)
    place_peak(fx, whoosh(0.5, 900, 2000, 900, 0.5, -0.6), 0.5, fr(A5['listIn']) + 0.25, 0.07)
    place(fx, riser(fr(A5['land']) - fr(A5['lift']) + 1.4, 300, 9000, 57, 0.45), fr(A5['lift']) - 1.4, 0.32)
    place_peak(fx, whoosh(0.5, 300, 2800, 600, 0.75, -0.9), 0.75, fr(A5['flyPeak']), 0.26)
    land = fr(A5['land'])
    place(fx, sub_boom(D_HZ * 2, D_HZ, 2.6, 0.08), land, 0.85)
    place(fx, snap(D_HZ * 2, 0.8, 1.0), land, 0.55)
    edge_ping(bells, land, 0.14, 1.4, step=0.06, notes=EDGE + [81])
    for i, f in enumerate(A5['shiftLands']):
        place(fx, wood(mtof(69 - i * 3), 0.1, 0.02, 0.4), fr(f) + 0.03, 0.09, pan=-0.4)
    ring = A5['ring']
    place(fx, whoosh(fr(ring['to']) - fr(ring['from']), 1200, 5000, 3000, 0.6, 0.4, 0.2), fr(ring['from']), 0.05)
    for i, f in enumerate(WORDS['knowWhere']):
        place(fx, filt(noise(0.04), sos('band', (900, 2600))) * np.exp(-tt(0.04) / 0.01), fr(f), 0.05)

    # ACT 6 - resolution
    place_peak(fx, whoosh(1.0, 1200, 400, 150, 0.4, 0.8), 0.4, fr(A6['rest']), 0.08)
    place_peak(fx, whoosh(0.6, 300, 1600, 500, 0.5, 0.5), 0.5, fr(A6['morphPeak']), 0.14)
    place(fx, snap(D_HZ * 2, 0.7, 0.8), fr(A6['tileLand']), 0.4)
    place_peak(fx, whoosh(0.5, 500, 3200, 1200, 0.4, 0.6), 0.4, fr(A6['wordmark']), 0.1)
    lock = fr(A6['lockup'])
    place(fx, sub_boom(D_HZ * 2, D_HZ, 3.0, 0.07), lock, 0.45)
    edge_ping(bells, lock, 0.15, 1.1, step=0.09, notes=[62, 69, 74, 78], tau=1.6)
    # bookend: the clock returns, calm and in time, and stops on the last beat
    end = buf()
    for k in range(1, 4):
        place(end, wood(mtof(81 + [0, 2, 3, 5, 7, 8, 10][0]), 0.12, 0.022, 0.2), lock + k * BEAT, 0.09 - 0.015 * k, pan=0.1)
    return fx, end


# ------------------------------------------------------------------------------------------------
# mix and master
# ------------------------------------------------------------------------------------------------
def sidechain(kicks, depth=0.5, tau=0.13):
    g = np.ones(N)
    t = np.arange(N) / SR
    for kt, kg in kicks:
        i = int(kt * SR)
        seg = t[i:i + int(0.5 * SR)] - kt
        g[i:i + len(seg)] = np.minimum(g[i:i + len(seg)], 1 - depth * kg * np.exp(-seg / tau))
    return g[:, None]


def envelope(points):
    t = np.arange(N) / SR
    ts, gs = zip(*points)
    return filt(np.interp(t, ts, gs), sos('low', 5, 1))[:, None]


def true_peak_limiter(x, ceiling, look=0.003, release=0.09):
    """Brick-wall limiter whose detector runs on a 4x oversampled signal (catches inter-sample peaks)."""
    up = signal.resample_poly(x, 4, 1, axis=0)
    a = np.max(np.abs(up), axis=1)
    a = a[: (len(a) // 4) * 4].reshape(-1, 4).max(axis=1)
    a = np.pad(a, (0, max(0, len(x) - len(a))))[: len(x)]
    la = int(look * SR)
    peak = np.maximum.reduce([np.roll(a, -k) for k in range(0, la, 4)])
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
    import pyloudnorm as pyln
    import soundfile as sf

    os.makedirs(os.path.join(ROOT, 'out', 'stems'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'public', 'audio'), exist_ok=True)
    m = build_music()
    fx, fx_end = build_sfx(m['bells'])
    t = np.arange(N) / SR

    sc = sidechain(m['kicks'])
    music = m['drums'] * 0.9 + m['bass'] * sc * 0.8 + m['pad'] * (0.6 + 0.4 * sc) * 1.5 + m['keys'] * (0.75 + 0.25 * sc) * 1.4 + m['bells'] * 1.4
    send = filt(m['pad'] * 0.25 + m['keys'] * 0.35 + m['bells'] * 0.7 + m['drums'] * 0.05, sos('high', 220))
    wet = reverb(send, IR_HALL)
    fxs = filt(fx, sos('high', 220))
    fxwet = reverb(fxs * 0.16, IR_ROOM) + reverb(fxs * 0.08, IR_HALL)

    # the hush before each drop: the whole bed ducks so the hit lands on near-silence
    rv, land = fr(C['drop1']), fr(C['land'])
    hush = np.ones(N)
    for a0, a1, depth in ((rv - 0.26, rv, 0.9), (land - 0.12, land, 0.75)):
        w = (t > a0) & (t < a1)
        hush = np.where(w, np.minimum(hush, 1 - depth * np.clip((t - a0) / 0.04, 0, 1)), hush)
    hush = hush[:, None]
    # music bus automation: quieter under the words, open on the drops
    bus = envelope([(0, 0.9), (fr(C['foundIt']) - 0.2, 0.9), (fr(C['foundIt']), 0.7), (fr(C['pullBack']), 0.85),
                    (rv, 1.0), (fr(C['fieldIn']), 0.9), (land - 0.1, 0.9), (land, 1.05), (fr(C['resolve']), 0.95), (DUR, 0.95)])

    mix = ((music + wet * 0.55) * bus * hush + (fx * 1.2 + fxwet) * np.maximum(hush, 0.35))
    mix = filt(mix, sos('high', 26, 2))
    # mono below 120 Hz
    mid = mix.mean(axis=1, keepdims=True)
    side = filt((mix[:, :1] - mix[:, 1:]) / 2, sos('high', 120))
    mix = np.concatenate([mid + side, mid - side], axis=1)
    # bus compressor: 2:1 above -16 dBFS (5 ms RMS detector), 12 ms attack, 140 ms release
    det = np.sqrt(filt(np.mean(mix ** 2, axis=1), sos('low', 1 / (2 * np.pi * 0.005), 1)).clip(1e-12))
    gr = -np.maximum(0, 20 * np.log10(det) + 16) * 0.5
    att, rel = np.exp(-1 / (0.012 * SR)), np.exp(-1 / (0.14 * SR))
    g = np.empty_like(gr)
    cur = 0.0
    for i, x in enumerate(gr):
        cur = x + (cur - x) * (att if x < cur else rel)
        g[i] = cur
    mix *= (10 ** (g / 20))[:, None]
    mix = sat(mix * 0.9, 1.1)
    mix += filt(mix, sos('high', 3000, 1)) * 0.18  # a little air

    # the ending: the lockup chord decays to silence exactly at 30.000 s; the clock rides on top
    fade = np.clip((END - 0.02 - t) / 1.4, 0, 1) ** 1.5
    mix *= fade[:, None]
    mix += filt(fx_end, sos('high', 220)) * 1.2 + reverb(filt(fx_end, sos('high', 220)) * 0.15, IR_ROOM)

    # loudness: -14 LUFS integrated, true-peak ceiling with headroom for the AAC encode
    meter = pyln.Meter(SR)
    for _ in range(4):
        body = mix[: int(END * SR)]
        lufs = meter.integrated_loudness(body)
        mix *= 10 ** ((-14.0 - lufs) / 20)
        mix = true_peak_limiter(mix, ceiling=10 ** (-2.2 / 20))
    mix = mix[: int(END * SR)]
    mix[-240:] *= np.linspace(1, 0, 240)[:, None]

    out = os.path.join(ROOT, 'public', 'audio', 'soundtrack.wav')
    sf.write(out, mix.astype(np.float32), SR, subtype='PCM_24')
    for k in ('drums', 'bass', 'pad', 'keys', 'bells'):
        sf.write(os.path.join(ROOT, 'out', 'stems', f'{k}.wav'), m[k][: len(mix)].astype(np.float32), SR)
    sf.write(os.path.join(ROOT, 'out', 'stems', 'sfx.wav'), fx[: len(mix)].astype(np.float32), SR)
    tp = 20 * np.log10(np.max(np.abs(signal.resample_poly(mix, 4, 1, axis=0))) + 1e-12)
    print(f'wrote {os.path.relpath(out, ROOT)}: {len(mix) / SR:.3f} s, {meter.integrated_loudness(mix):.2f} LUFS, '
          f'true peak {tp:.2f} dBTP (source)')


if __name__ == '__main__':
    main()
