#!/usr/bin/env bash
# Render the review MP4: cues → soundtrack → embedded audio → frames (with motion blur) → mux.
# Mirrors the reference film's render.sh: the picture is rendered silent from the same timeline
# the score was built from, and the soundtrack is muxed with ffmpeg.
#
# Usage: tools/render-preview.sh [out.mp4] [--sub N] [--scale K] [--jobs J]
#   --sub N    sub-frames per frame for motion blur (default 3; 1 = sharp, much faster)
#   --scale K  1 = 1920×1080 (default), 0.5 = 960×540
#   --jobs J   parallel browsers, each rendering a slice of the film (default: CPU count)
# Needs: node + playwright-core (+ Chromium, CHROMIUM_PATH), python3 numpy scipy soundfile
#        pyloudnorm Pillow, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-out/applicable-opening.mp4}
shift || true
SUB=3; SCALE=1; JOBS=$(nproc 2>/dev/null || echo 2)
while [[ $# -gt 0 ]]; do case "$1" in --sub) SUB=$2; shift 2;; --scale) SCALE=$2; shift 2;; --jobs) JOBS=$2; shift 2;; *) shift;; esac; done
mkdir -p "$(dirname "$OUT")"
if [[ "${SKIP_AUDIO:-}" != 1 ]]; then
  node tools/export-cues.mjs
  python3 tools/soundtrack.py
  node tools/embed-audio.mjs
fi
TMP=$(mktemp -d /tmp/aa-renderXXXXXX)
trap 'rm -rf "$TMP"' EXIT
DUR=$(python3 -c "import json; print(json.load(open('audio/cues.json'))['duration'])")
DIR="$TMP/frames"; [[ "$SUB" -gt 1 ]] && DIR="$TMP/sub"
for ((j = 0; j < JOBS; j++)); do
  A=$(python3 -c "print(round($DUR * $j / $JOBS * 30) / 30)")
  B=$(python3 -c "print(round($DUR * ($j + 1) / $JOBS * 30) / 30)")
  node tools/capture.mjs video "$DIR" --fps 30 --sub "$SUB" --scale "$SCALE" --from "$A" --to "$B" &
done
wait
if [[ "$SUB" -gt 1 ]]; then python3 tools/accumulate.py "$TMP/sub" "$TMP/frames"; fi
ffmpeg -loglevel error -y -framerate 30 -i "$TMP/frames/%05d.png" -i audio/soundtrack.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 256k \
  -movflags +faststart -shortest "$OUT"
echo "wrote $OUT"
