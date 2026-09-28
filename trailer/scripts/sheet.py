#!/usr/bin/env python3
"""Contact sheets for frame-by-frame review.

Renders (or extracts) every Nth frame of a range, stamps each with its frame number and timecode,
and tiles them into one PNG. Two sources:

  --comp <id>     render the frames with Remotion from the composition (sharp, current source)
  --video <mp4>   decode the frames from a rendered film (checks what was actually delivered)

Usage:
  python3 scripts/sheet.py --comp Launch --range 0 1799 --every 60 --out out/contact-sheet.png
  python3 scripts/sheet.py --video out/applicable-launch-final.mp4 --range 1500 1799 --every 12 --out out/sheet-lockup.png
  python3 scripts/sheet.py --comp Launch --frames 0,180,600 --out out/sheet-keys.png
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ROOT  # noqa: E402

FPS = 60


def label_font(size):
    for path in (os.path.join(ROOT, 'public', 'fonts', 'figtree-latin-700-normal.woff2'),
                 '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_frames(comp, frames, tmp):
    cmd = ['npx', 'remotion', 'render', comp, tmp, '--props={"withAudio":false}', '--sequence', f'--frames={",".join(map(str, frames))}',
           '--image-format=jpeg', '--jpeg-quality=92', '--log=error']
    subprocess.run(cmd, cwd=ROOT, check=True)
    files = sorted(glob.glob(os.path.join(tmp, '*.jpeg')))
    if len(files) != len(frames):
        raise SystemExit(f'expected {len(frames)} frames, got {len(files)}')
    return files


def extract_frames(video, frames, tmp):
    """Decode the requested frames of a delivered file (sequential decode: exact frame indices)."""
    import cv2
    cap = cv2.VideoCapture(video)
    want = set(frames)
    files, n = [], 0
    while want and n <= max(frames):
        ok, img = cap.read()
        if not ok:
            break
        if n in want:
            p = os.path.join(tmp, f'v_{n:05d}.png')
            cv2.imwrite(p, img)
            files.append(p)
            want.discard(n)
        n += 1
    if want:
        raise SystemExit(f'frames not found in {video}: {sorted(want)}')
    return files


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--comp')
    src.add_argument('--video')
    ap.add_argument('--range', nargs=2, type=int, metavar=('FROM', 'TO'))
    ap.add_argument('--every', type=int, default=60)
    ap.add_argument('--frames', help='explicit comma-separated frame list')
    ap.add_argument('--cols', type=int, default=5)
    ap.add_argument('--width', type=int, default=480, help='tile width in px')
    ap.add_argument('--title', default='')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    if a.frames:
        frames = [int(x) for x in a.frames.split(',')]
    elif a.range:
        frames = list(range(a.range[0], a.range[1] + 1, a.every))
    else:
        raise SystemExit('give --range or --frames')

    with tempfile.TemporaryDirectory(prefix='sheet') as tmp:
        files = render_frames(a.comp, frames, tmp) if a.comp else extract_frames(a.video, frames, tmp)
        tiles = [Image.open(p).convert('RGB') for p in files]
        w = a.width
        h = round(tiles[0].height * w / tiles[0].width)
        cols = min(a.cols, len(tiles))
        rows = (len(tiles) + cols - 1) // cols
        pad, head = 6, (44 if a.title else 0)
        sheet = Image.new('RGB', (cols * (w + pad) + pad, rows * (h + pad) + pad + head), (40, 42, 46))
        draw = ImageDraw.Draw(sheet)
        font = label_font(max(14, w // 26))
        if a.title:
            draw.text((pad + 4, 10), a.title, fill=(235, 236, 238), font=label_font(24))
        for i, (img, fr) in enumerate(zip(tiles, frames)):
            x = pad + (i % cols) * (w + pad)
            y = head + pad + (i // cols) * (h + pad)
            sheet.paste(img.resize((w, h), Image.LANCZOS), (x, y))
            text = f'f{fr}  {fr / FPS:05.2f}s'
            tb = draw.textbbox((0, 0), text, font=font)
            draw.rectangle((x, y, x + tb[2] + 12, y + tb[3] + 8), fill=(0, 0, 0))
            draw.text((x + 6, y + 3), text, fill=(255, 255, 255), font=font)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        sheet.save(a.out)
        print(f'{a.out} ({len(frames)} frames)')


if __name__ == '__main__':
    main()
