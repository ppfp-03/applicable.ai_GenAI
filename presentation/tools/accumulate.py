#!/usr/bin/env python3
"""Average each frame's sub-frames (NNNNN_k.png) into NNNNN.png: temporal motion blur.

As in the reference film's accumulate.py, samples are averaged in floating point and
quantised once, so soft gradients stay smooth.  Usage: accumulate.py <sub_dir> <out_dir>
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
groups = defaultdict(list)
for p in sorted(src.glob('*_*.png')):
    groups[p.stem.split('_')[0]].append(p)
rng = np.random.default_rng(1)
for name, parts in sorted(groups.items()):
    acc = None
    for p in parts:
        a = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32)
        acc = a if acc is None else acc + a
    acc /= len(parts)
    acc += rng.uniform(-0.5, 0.5, acc.shape).astype(np.float32)  # dither before the one quantisation
    Image.fromarray(np.clip(np.rint(acc), 0, 255).astype(np.uint8)).save(dst / f'{name}.png')
print(f'{len(groups)} frames accumulated')
