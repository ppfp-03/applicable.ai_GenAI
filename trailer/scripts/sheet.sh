#!/usr/bin/env bash
# QA contact sheets: the whole film plus tight sheets around the key moments.
# Default source is the delivered final film (what viewers get); pass --comp to render from source.
#   scripts/sheet.sh                      sheets from out/applicable-launch-final.mp4
#   scripts/sheet.sh --comp               sheets rendered sharp from the Launch composition
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-.venv/bin/python}
if [[ "${1:-}" == "--comp" ]]; then SRC=(--comp Launch); else SRC=(--video "${VIDEO:-out/applicable-launch-final.mp4}"); fi
"$PY" scripts/sheet.py "${SRC[@]}" --range 0 1799 --every 45 --cols 8 --width 360 --title "Applicable.ai launch film - every 0.75 s" --out out/contact-sheet.png
"$PY" scripts/sheet.py "${SRC[@]}" --range 0 359 --every 18 --cols 5 --width 480 --title "0:00-0:06 too late (100+ at f180)" --out out/sheet-act1.png
"$PY" scripts/sheet.py "${SRC[@]}" --range 168 204 --every 3 --cols 5 --width 480 --title "the 100+ transition" --out out/sheet-100.png
"$PY" scripts/sheet.py "${SRC[@]}" --range 552 720 --every 8 --cols 6 --width 400 --title "around 0:10: the reveal" --out out/sheet-reveal.png
"$PY" scripts/sheet.py "${SRC[@]}" --range 1200 1500 --every 15 --cols 5 --width 480 --title "0:20-0:25 act first" --out out/sheet-payoff.png
"$PY" scripts/sheet.py "${SRC[@]}" --range 1500 1799 --every 15 --cols 5 --width 480 --title "0:25-0:30 lockup" --out out/sheet-lockup.png
