"""Locates ffmpeg / ffprobe for the Python tools.

Order: $FFMPEG / $FFPROBE, then binaries on PATH, then the ones Remotion ships with its compositor
(node_modules/@remotion/compositor-*), which need their own directory on the dynamic-library path.
"""
import glob
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find(name):
    env = os.environ.get(name.upper())
    if env:
        return env, dict(os.environ)
    on_path = shutil.which(name)
    if on_path:
        return on_path, dict(os.environ)
    for d in sorted(glob.glob(os.path.join(ROOT, 'node_modules', '@remotion', 'compositor-*'))):
        exe = os.path.join(d, name)
        if os.path.isfile(exe):
            env = dict(os.environ)
            for var in ('DYLD_LIBRARY_PATH', 'LD_LIBRARY_PATH'):
                env[var] = d + (os.pathsep + env[var] if env.get(var) else '')
            return exe, env
    raise SystemExit(f'{name} not found: install it or run `npm install` so Remotion provides one')


FFMPEG, FFMPEG_ENV = _find('ffmpeg')
FFPROBE, FFPROBE_ENV = _find('ffprobe')
