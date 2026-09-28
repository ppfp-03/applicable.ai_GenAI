#!/usr/bin/env python3
"""Decides how many motion-blur samples each output frame needs, from how fast things move on screen.

Optical flow on the sharp render gives, per frame, the speed of the fastest-moving content (only
pixels that actually change count). Dense Farneback flow sees large moving surfaces (a pushing
camera, the market drifting); pyramidal Lucas-Kanade on tracked corners, checked forward-backward,
sees small fast objects that dense flow smooths away (a card flying into #1, a cursor, a wavefront).
The faster of the two sets the speed. Each frame is then rendered as n sub-frames spread across the
shutter so neighbouring samples are at most STEP px apart: fast moves smear instead of stamping
copies, and still frames render once.

Usage: python3 scripts/measure-speed.py <sharp.mp4> <out/samples.json>
"""
import json
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUES = json.load(open(os.path.join(ROOT, 'out', 'cues.json')))
SHUTTER = CUES['shutter'] / 360  # fraction of the frame interval the shutter is open (src/blur.ts)
STEP = 3.0  # max px between neighbouring samples, at 1080p
N_MIN, N_MAX = 3, 40
STILL = 1.2  # px/frame below which a frame renders once
AW, AH = 960, 540  # analysis resolution
K = 1920 / AW

src, out = sys.argv[1:3]
cap = cv2.VideoCapture(src)
frames = []
while True:
    ok, img = cap.read()
    if not ok:
        break
    frames.append(cv2.cvtColor(cv2.resize(img, (AW, AH), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
if len(frames) != CUES['total']:
    raise SystemExit(f'{src}: {len(frames)} frames, expected {CUES["total"]}')

LK = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
v = [0.0]  # v[i]: speed of the move from frame i-1 to frame i, px/frame at 1080p
for a, b in zip(frames, frames[1:]):
    moving = cv2.absdiff(a, b) > 5
    if moving.sum() < 30:
        v.append(0.0)
        continue
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 5, 21, 3, 7, 1.5, 0)
    dense = float(np.percentile(np.hypot(flow[..., 0], flow[..., 1])[moving], 95))
    sparse = 0.0
    pts = cv2.goodFeaturesToTrack(a, 600, 0.01, 5, mask=cv2.dilate(moving.astype(np.uint8), None, iterations=4))
    if pts is not None:
        fwd, s1, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, **LK)
        back, s2, _ = cv2.calcOpticalFlowPyrLK(b, a, fwd, None, **LK)
        good = (s1[:, 0] == 1) & (s2[:, 0] == 1) & (np.linalg.norm((back - pts)[:, 0], axis=1) < 1.0)
        if good.sum() >= 3:
            sparse = float(np.percentile(np.linalg.norm((fwd - pts)[good, 0], axis=1), 98))
    v.append(max(dense, sparse) * K)

# the shutter of frame i spans motion on both sides of it
speed = [max(v[i], v[i + 1] if i + 1 < len(v) else 0.0) for i in range(len(v))]
groups = [1 if s < STILL else int(min(N_MAX, max(N_MIN, math.ceil(SHUTTER * s / STEP)))) for s in speed]
json.dump({'groups': groups, 'speed': [round(s, 2) for s in speed], 'shutter_deg': CUES['shutter'], 'step_px': STEP}, open(out, 'w'))
h = np.bincount(np.minimum(groups, N_MAX), minlength=N_MAX + 1)
print(f'{len(groups)} frames -> {sum(groups)} sub-frames; still {h[1]}, 3-8: {h[3:9].sum()}, 9-20: {h[9:21].sum()}, '
      f'21+: {h[21:].sum()}; peak {max(speed):.0f} px/frame (f{int(np.argmax(speed))})')
