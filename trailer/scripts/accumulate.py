#!/usr/bin/env python3
"""Temporal motion blur by accumulation, outside the browser.

Reads the LaunchSub sub-frame render (a lossless PNG sequence straight from Chromium), averages each
output frame's group of sub-frames in float32, adds a +-1 LSB triangular (TPDF) dither and hands a
16-bit frame to ffmpeg, which converts to BT.709 4:2:0 once and encodes H.264. The picture is
quantized exactly once; soft gradients stay smooth and static pixels stay exact.

Usage: python3 scripts/accumulate.py <subframes_dir> <samples.json> <out.mp4>
"""
import glob
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FFMPEG, FFMPEG_ENV  # noqa: E402

src, groups_path, out = sys.argv[1:4]
groups = json.load(open(groups_path))['groups']
files = sorted(glob.glob(os.path.join(src, '*.png')))
if len(files) != sum(groups):
    raise SystemExit(f'{len(files)} sub-frames on disk, samples.json expects {sum(groups)}')

enc = subprocess.Popen(
    [FFMPEG, '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '60', '-c:v', 'png', '-i', '-',
     '-vf', 'scale=in_range=full:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int+bitexact,format=yuv420p',
     '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('ACCUM_CRF', '13'), '-profile:v', 'high',
     '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv',
     '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
     '-movflags', '+faststart', out],
    stdin=subprocess.PIPE, env=FFMPEG_ENV)

rng = np.random.default_rng(7)
H, W = 1080, 1920
DITHER = [((rng.random((H, W, 3), dtype=np.float32) + rng.random((H, W, 3), dtype=np.float32)) - 1.0) * 257.0 for _ in range(8)]
acc = np.zeros((H, W, 3), np.float32)
k = 0
for i, n in enumerate(groups):
    acc[:] = 0
    for _ in range(n):
        img = cv2.imread(files[k], cv2.IMREAD_UNCHANGED)
        k += 1
        if img.ndim == 3 and img.shape[2] == 4:
            img = img[:, :, :3]
        acc += img.astype(np.float32) * (257.0 if img.dtype == np.uint8 else 1.0)
    acc /= n
    if n > 1:
        acc += DITHER[i % len(DITHER)]
        frame = np.clip(acc + 0.5, 0, 65535).astype(np.uint16)
    else:
        frame = np.clip(acc + 0.5, 0, 65535).astype(np.uint16)  # a still frame: the exact render
    ok, png = cv2.imencode('.png', frame, [cv2.IMWRITE_PNG_COMPRESSION, 1])
    enc.stdin.write(png.tobytes())
    if i % 300 == 0:
        print(f'  accumulated {i}/{len(groups)} frames', flush=True)
enc.stdin.close()
if enc.wait() != 0:
    raise SystemExit('encode failed')
print(f'wrote {out}: {len(groups)} frames from {k} sub-frames')
