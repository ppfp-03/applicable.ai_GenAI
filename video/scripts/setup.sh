#!/usr/bin/env bash
# Installs everything the video pipeline needs: Node packages (Remotion),
# ffmpeg for muxing, and the Python libraries for soundtrack synthesis,
# loudness mastering and motion-blur accumulation.
# Usage: npm run setup
set -euo pipefail
cd "$(dirname "$0")/.."

npm install

if ! command -v ffmpeg >/dev/null; then
  if command -v apt-get >/dev/null; then
    SUDO=$([ "$(id -u)" = 0 ] && echo "" || echo sudo)
    $SUDO apt-get update -qq || true
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq ffmpeg bc libsndfile1
  elif command -v brew >/dev/null; then
    brew install ffmpeg libsndfile
  else
    echo "Install ffmpeg manually, then re-run." >&2
    exit 1
  fi
fi

python3 -m pip install -q -r requirements-audio.txt
python3 -c "import numpy, scipy, soundfile, pyloudnorm, cv2, PIL"
echo "Video toolchain ready: remotion $(node -p "require('remotion/package.json').version"), $(ffmpeg -version | head -1 | cut -d' ' -f1-3)"
