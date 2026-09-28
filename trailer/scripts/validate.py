#!/usr/bin/env python3
"""Delivery check with ffprobe: exact duration and frame count, 60 fps, 1920x1080, H.264 yuv420p
BT.709, AAC 48 kHz stereo at ~320 kb/s, both streams starting at 0. Prints the observed values and
exits 1 if any spec is missed.

Usage: python3 scripts/validate.py <film.mp4>
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FFPROBE, FFPROBE_ENV  # noqa: E402

path = sys.argv[1]
p = json.loads(subprocess.run([FFPROBE, '-v', 'error', '-count_frames', '-show_format', '-show_streams', '-of', 'json', path],
                              capture_output=True, text=True, check=True, env=FFPROBE_ENV).stdout)
v = next(s for s in p['streams'] if s['codec_type'] == 'video')
a = next(s for s in p['streams'] if s['codec_type'] == 'audio')
num, den = map(int, v['r_frame_rate'].split('/'))
checks = [
    ('frames', int(v['nb_read_frames']), lambda x: x == 1800),
    ('fps', num / den, lambda x: abs(x - 60) < 1e-9),
    ('video duration s', float(v['duration']), lambda x: abs(x - 30.0) < 1e-6),
    ('container duration s', float(p['format']['duration']), lambda x: abs(x - 30.0) < 0.03),
    ('width', v['width'], lambda x: x == 1920),
    ('height', v['height'], lambda x: x == 1080),
    ('video codec', v['codec_name'], lambda x: x == 'h264'),
    ('pixel format', v['pix_fmt'], lambda x: x == 'yuv420p'),
    ('color space', v.get('color_space'), lambda x: x == 'bt709'),
    ('color primaries', v.get('color_primaries'), lambda x: x == 'bt709'),
    ('color transfer', v.get('color_transfer'), lambda x: x == 'bt709'),
    ('video start s', float(v['start_time']), lambda x: x == 0),
    ('audio codec', a['codec_name'], lambda x: x == 'aac'),
    ('audio profile (AAC-LC)', a.get('profile'), lambda x: x in ('LC', '1')),  # this ffprobe build prints the id
    ('sample rate', int(a['sample_rate']), lambda x: x == 48000),
    ('channels', a['channels'], lambda x: x == 2),
    ('audio bitrate kb/s', round(int(a.get('bit_rate', 0)) / 1000), lambda x: 256 <= x <= 330),
    ('audio start s', float(a['start_time']), lambda x: x == 0),
    ('audio duration s', float(a['duration']), lambda x: abs(x - 30.0) < 0.03),
]
# faststart: the moov atom must precede mdat
data = open(path, 'rb').read(1 << 20)
moov, mdat = data.find(b'moov'), data.find(b'mdat')
checks.append(('faststart (moov before mdat)', 0 <= moov < (mdat if mdat >= 0 else 1 << 30), lambda x: x is True))
bad = 0
for name, val, ok in checks:
    good = ok(val)
    bad += not good
    print(f"  {'ok ' if good else 'BAD'} {name:28s} {val}")
print(f"video bitrate {int(v.get('bit_rate', 0)) / 1e6:.1f} Mb/s, size {os.path.getsize(path) / 1e6:.1f} MB")
print('delivery spec OK' if not bad else f'delivery spec FAILED ({bad})')
sys.exit(1 if bad else 0)
