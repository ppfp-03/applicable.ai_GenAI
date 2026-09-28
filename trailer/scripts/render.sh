#!/usr/bin/env bash
# Renders the film. Picture from Remotion (muted), soundtrack muxed afterwards by ffmpeg, then the
# automatic A/V sync + true-peak check. Remotion's own AAC mux keeps the encoder priming in the
# stream (a measurable audio lag), so the audio is always attached here and verified.
#
#   scripts/render.sh preview   sharp picture (no motion blur)       -> out/applicable-launch-preview.mp4
#   scripts/render.sh final     temporal motion blur (see src/blur.ts) -> out/applicable-launch-final.mp4
#
# The final path: a sharp render is measured with optical flow (measure-speed.py -> out/samples.json),
# Remotion renders the LaunchSub sub-frame stream, accumulate.py averages it in float32 and encodes once.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-.venv/bin/python}
MODE=${1:-preview}
CONC=${CONCURRENCY:-6}
mkdir -p out
npx tsx scripts/export-cues.ts
"$PY" scripts/soundtrack.py
TMP=$(mktemp -d "${TMPDIR:-/tmp}/applicable-render-XXXXXX")
trap 'rm -rf "$TMP"' EXIT
NOAUDIO='{"withAudio":false}'

case "$MODE" in
  preview)
    OUT=out/applicable-launch-preview.mp4
    npx remotion render Launch "$TMP/picture.mp4" --props="$NOAUDIO" --muted --codec=h264 \
      --crf=16 --x264-preset=medium --pixel-format=yuv420p --color-space=bt709 --concurrency="$CONC" --log=error
    ;;
  final)
    OUT=out/applicable-launch-final.mp4
    SHARP=${SHARP:-out/sharp.mp4}
    if [[ ! -f "$SHARP" ]]; then
      npx remotion render Launch "$SHARP" --props="$NOAUDIO" --muted --codec=h264 --crf=12 \
        --x264-preset=veryfast --pixel-format=yuv420p --concurrency="$CONC" --log=error
    fi
    "$PY" scripts/measure-speed.py "$SHARP" out/samples.json
    # sub-frames as a lossless PNG sequence: nothing is quantized twice before accumulation
    npx remotion render LaunchSub "$TMP/sub" --props=out/samples.json --sequence --image-format=png \
      --concurrency="$CONC" --log=error
    "$PY" scripts/accumulate.py "$TMP/sub" out/samples.json "$TMP/picture.mp4"
    ;;
  *)
    echo "usage: scripts/render.sh preview|final" >&2
    exit 2
    ;;
esac

"$PY" scripts/mux.py "$TMP/picture.mp4" public/audio/soundtrack.wav "$OUT"
"$PY" scripts/check-sync.py "$OUT"
echo "$OUT"
