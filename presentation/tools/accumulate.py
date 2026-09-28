#!/usr/bin/env python3
"""Reduce and average each frame's sub-frames (NNNNN_k.png) into NNNNN.png.

Every sub-frame is first brought to the output size with a Lanczos filter (supersampled
captures, e.g. capture.mjs --dsf 2, come in at 3840×2160), then the samples are averaged:
temporal motion blur when there are several, a plain reduction when there is one.  As in the
reference film's accumulate.py, the average is kept in floating point and quantised once, so
soft gradients stay smooth.

Usage: accumulate.py <sub_dir> <out_dir> [--size 1920x1080] [--jobs N] [--delete]
  --delete  remove each frame's sub-frames once it is written (renders in blocks to save disk)
"""
import argparse
import os
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('src', type=Path)
ap.add_argument('dst', type=Path)
ap.add_argument('--size', default='1920x1080')
ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
ap.add_argument('--delete', action='store_true')
args = ap.parse_args()
size = tuple(int(x) for x in args.size.split('x'))


def load(p):
    im = Image.open(p).convert('RGB')
    if im.size != size:
        im = im.resize(size, Image.LANCZOS, reducing_gap=None)
    return np.asarray(im, dtype=np.float32)


def frame(item):
    name, parts = item
    acc = None
    for p in parts:
        a = load(p)
        acc = a if acc is None else acc + a
    acc /= len(parts)
    rng = np.random.default_rng(int(name))  # per-frame seed: same result however it is split
    acc += rng.uniform(-0.5, 0.5, acc.shape).astype(np.float32)  # dither before the one quantisation
    Image.fromarray(np.clip(np.rint(acc), 0, 255).astype(np.uint8)).save(args.dst / f'{name}.png')
    if args.delete:
        for p in parts:
            p.unlink()


if __name__ == '__main__':
    args.dst.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for p in sorted(args.src.glob('*_*.png')):
        groups[p.stem.split('_')[0]].append(p)
    with Pool(args.jobs) as pool:
        pool.map(frame, sorted(groups.items()), chunksize=4)
    print(f'{len(groups)} frames accumulated at {size[0]}×{size[1]}')
