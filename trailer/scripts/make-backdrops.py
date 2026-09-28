#!/usr/bin/env python3
"""Bakes the film's soft backdrops as dithered PNGs (public/fx/).

Chromium composites CSS gradients in 8 bits, so a glow that spans only a few code values (the
product's peach glows on #F5F6F8, the lift in the dark market, the text scrims) renders as contour
rings. These images compute the same gradients in float64 and quantize once with a +-1 LSB
triangular (TPDF) dither, so the steps disappear.

Usage: python3 scripts/make-backdrops.py
"""
import os

import numpy as np
from PIL import Image

W, H = 1920, 1080
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public', 'fx')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def grid(w, h):
    y, x = np.mgrid[0:h, 0:w].astype(np.float64) + 0.5
    return x / w, y / h


def rho(x, y, cx, cy, rx, ry):
    """Elliptical distance, 1.0 on the ellipse (like CSS radial-gradient ellipse rx ry at cx cy)."""
    return np.hypot((x - cx) / rx, (y - cy) / ry)


def smooth_falloff(r):
    """1 at the centre, 0 at r >= 1, with zero slope at both ends (no visible rim)."""
    t = np.clip(1 - r, 0, 1)
    return t * t * (3 - 2 * t)


def tpdf(shape):
    return rng.random(shape) + rng.random(shape) - 1.0


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64)


def save_rgb(rgb, name):
    q = np.clip(np.round(rgb + tpdf(rgb.shape[:2])[..., None]), 0, 255).astype(np.uint8)
    Image.fromarray(q, 'RGB').save(os.path.join(OUT, name), optimize=True)


def save_alpha(color, a, name):
    """A flat-colour layer whose alpha carries the gradient (dithered in alpha)."""
    alpha = np.clip(np.round(a * 255 + tpdf(a.shape)), 0, 255).astype(np.uint8)
    h, w = a.shape
    rgb = np.broadcast_to(hexrgb(color).astype(np.uint8), (h, w, 3))
    Image.fromarray(np.dstack([rgb, alpha]), 'RGBA').save(os.path.join(OUT, name), optimize=True)


x, y = grid(W, H)

# 1. The product's ground: #F5F6F8 with the warm peach glows of the live app (top-left, right)
#    and the faint mint glow at the bottom edge (ui/css/base.css, mapped by ui/palette.py).
base = hexrgb('#F5F6F8')
rgb = np.broadcast_to(base, (H, W, 3)).copy()
for (cx, cy, rx, ry, col, k) in [
    (0.06, 0.02, 0.42, 0.62, '#FBD3BE', 0.85),  # peach, top-left
    (0.97, 0.38, 0.30, 0.55, '#FCDCCB', 0.70),  # peach, right
    (0.46, 1.08, 0.36, 0.22, '#DDEFE4', 0.55),  # mint, bottom
]:
    t = smooth_falloff(rho(x, y, cx, cy, rx, ry))[..., None] * k
    rgb = rgb * (1 - t) + hexrgb(col) * t
save_rgb(rgb, 'app-bg.png')

# 2. The market at night: near-black with a cool lift behind the lanes and a soft vignette.
base = hexrgb('#0D0E11')
lift = hexrgb('#171A20')
t = smooth_falloff(rho(x, y, 0.62, 0.5, 0.75, 0.8))[..., None]
rgb = base * (1 - t) + lift * t
vig = np.clip(rho(x, y, 0.5, 0.5, 0.78, 0.78) - 0.55, 0, 1)[..., None]
rgb = rgb * (1 - 0.55 * vig)
save_rgb(rgb, 'void-bg.png')

# 3. Dark scrim for headlines over the market: an elliptical pool of shadow.
a = 0.86 * smooth_falloff(rho(x, y, 0.5, 0.5, 0.46, 0.34)) ** 0.8
save_alpha('#0D0E11', a, 'scrim-dark.png')

# 4. Light scrim for headlines over the blurred job board.
a = 0.93 * smooth_falloff(rho(x, y, 0.5, 0.47, 0.56, 0.42)) ** 0.7
save_alpha('#F2F3F5', a, 'scrim-light.png')

# 5. The now edge's glow: a tall soft beam (drawn centred on the line, scaled by CSS).
bw, bh = 640, 1400
bx, by = grid(bw, bh)
beam = np.exp(-((bx - 0.5) / 0.16) ** 2) * smooth_falloff(np.abs(by - 0.5) / 0.5) ** 0.5
save_alpha('#F26A3D', beam, 'glow-orange.png')
save_alpha('#E9EBEF', beam, 'glow-white.png')

print('wrote', ', '.join(sorted(f for f in os.listdir(OUT) if f.endswith('.png'))))
