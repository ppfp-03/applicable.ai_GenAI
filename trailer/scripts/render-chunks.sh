#!/usr/bin/env bash
# Optional parallel render of the sharp preview: the composition is bundled once, the 1800 frames
# are split into contiguous ranges rendered by independent Remotion processes (one Chromium each),
# the parts are concatenated losslessly (stream copy) and the soundtrack is muxed and checked.
# Measured on the 8-core M2 used here: 3 chunks 77 s vs 90 s for render.sh preview (about 15%
# faster, identical frame count and specs), so it is kept as an option; render.sh stays the default.
#
# Usage: scripts/render-chunks.sh [chunks=3] [out=out/applicable-launch-preview-chunked.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-.venv/bin/python}
CHUNKS=${1:-3}
OUT=${2:-out/applicable-launch-preview-chunked.mp4}
npx tsx scripts/export-cues.ts >/dev/null
"$PY" scripts/soundtrack.py >/dev/null
TOTAL=$("$PY" -c "import json;print(json.load(open('out/cues.json'))['total'])")
TMP=$(mktemp -d "${TMPDIR:-/tmp}/applicable-chunks-XXXXXX")
trap 'rm -rf "$TMP"' EXIT
npx remotion bundle src/index.ts --out-dir "$TMP/bundle" --log=error >/dev/null
PER=$(( (TOTAL + CHUNKS - 1) / CHUNKS ))
PIDS=()
for ((i = 0; i < CHUNKS; i++)); do
  A=$(( i * PER )); B=$(( (i + 1) * PER - 1 )); (( B >= TOTAL )) && B=$(( TOTAL - 1 ))
  npx remotion render "$TMP/bundle" Launch "$TMP/part$i.mp4" --frames="$A-$B" --props='{"withAudio":false}' --muted \
    --codec=h264 --crf=16 --x264-preset=medium --pixel-format=yuv420p --color-space=bt709 \
    --concurrency=$(( 6 / CHUNKS > 0 ? 6 / CHUNKS : 1 )) --log=error &
  PIDS+=($!)
done
for p in "${PIDS[@]}"; do wait "$p"; done
for ((i = 0; i < CHUNKS; i++)); do echo "file '$TMP/part$i.mp4'"; done > "$TMP/list.txt"
"$PY" - "$TMP/list.txt" "$TMP/picture.mp4" <<'PYEOF'
import subprocess, sys, os
sys.path.insert(0, 'scripts')
from ff import FFMPEG, FFMPEG_ENV
subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', sys.argv[1], '-c', 'copy', sys.argv[2]],
               check=True, env=FFMPEG_ENV)
PYEOF
"$PY" scripts/mux.py "$TMP/picture.mp4" public/audio/soundtrack.wav "$OUT"
"$PY" scripts/check-sync.py "$OUT"
echo "$OUT"
