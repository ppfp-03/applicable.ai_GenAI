#!/usr/bin/env python3
"""Verifies the delivered audio: A/V sync and true peak, measured on the decoded AAC of the final file.

Sync: the master WAV is cross-correlated against the decoded stream around the film's transients
(the 100+ hit, the reveal drop, the landing, the lockup). The worst lag must be <= 1 ms (48 samples).
The audio stream must also start at t = 0 like the video stream.
True peak: 4x oversampled peak of the decoded stream must be <= -1 dBTP.
Exit code 1 on any failure.

Usage: python3 scripts/check-sync.py <film.mp4> [soundtrack.wav]
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FFMPEG, FFMPEG_ENV, FFPROBE, FFPROBE_ENV, ROOT  # noqa: E402

video = sys.argv[1]
ref, sr = sf.read(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'public', 'audio', 'soundtrack.wav'), always_2d=True)
cues = json.load(open(os.path.join(ROOT, 'out', 'cues.json')))
fps = cues['fps']

probe = json.loads(subprocess.run([FFPROBE, '-v', 'error', '-show_streams', '-of', 'json', video],
                                  capture_output=True, text=True, check=True, env=FFPROBE_ENV).stdout)
starts = {s['codec_type']: float(s.get('start_time', 'nan')) for s in probe['streams']}
print(f"  stream start: video {starts.get('video')} s, audio {starts.get('audio')} s")
start_ok = abs(starts.get('video', 1) - 0) < 1e-6 and abs(starts.get('audio', 1) - 0) < 1e-6

# decode the delivered AAC exactly as a player would (24-bit PCM is far below the AAC noise floor)
with tempfile.TemporaryDirectory() as tmp:
    wav = os.path.join(tmp, 'decoded.wav')
    subprocess.run([FFMPEG, '-v', 'error', '-i', video, '-map', '0:a:0', '-c:a', 'pcm_s24le', '-ac', '2', '-ar', str(sr), wav],
                   check=True, env=FFMPEG_ENV)
    dec, _ = sf.read(wav, always_2d=True)

points = {
    '100+ hit': cues['act1']['hundred'],
    'reveal drop': cues['act3']['drop'],
    'fresh emerge': cues['act4']['emerge'][0]['f'],
    'landing #1': cues['act5']['land'],
    'lockup': cues['act6']['lockup'],
}
SEARCH = 4800  # +-100 ms
worst = 0
for name, f in points.items():
    t = f / fps
    a, b = int((t - 0.15) * sr), int((t + 0.6) * sr)
    r = ref[a:b].mean(axis=1)
    d = dec[a - SEARCH:b + SEARCH].mean(axis=1)
    c = signal.correlate(d, r, mode='valid')
    lag = int(np.argmax(c)) - SEARCH
    # sub-sample refinement (parabolic) for the report
    k = int(np.argmax(c))
    frac = 0.0
    if 0 < k < len(c) - 1:
        y0, y1, y2 = c[k - 1], c[k], c[k + 1]
        frac = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
    worst = max(worst, abs(lag + frac))
    print(f'  {name:13s} t={t:6.3f}s  lag {lag + frac:+.2f} samples ({(lag + frac) / sr * 1000:+.3f} ms)')
ok = worst <= 48 and start_ok
print(f"sync {'OK' if ok else 'FAIL'}: worst {worst:.2f} samples = {worst / sr * 1000:.3f} ms (limit 1 ms)")

tp = 20 * np.log10(np.max(np.abs(signal.resample_poly(dec, 4, 1, axis=0))) + 1e-12)
tp_ok = tp <= -1.0
print(f"true peak (decoded AAC, 4x oversampled) {tp:.2f} dBTP {'OK' if tp_ok else 'FAIL (above -1 dBTP)'}")
try:
    import pyloudnorm as pyln
    print(f'integrated loudness (decoded AAC) {pyln.Meter(sr).integrated_loudness(dec):.2f} LUFS')
except ImportError:
    pass
sys.exit(0 if ok and tp_ok else 1)
