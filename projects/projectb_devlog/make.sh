#!/usr/bin/env bash
# Full pipeline: prepare assets -> build .blend -> render -> loudness-normalise.
# Usage: bash make.sh [prepare|build|render|final|all]   (default: all)
# Needs ProjectB (screenshots + voxel models): set PROJECTB_ROOT if it isn't D:\UnityProjects\ProjectB.
set -euo pipefail
cd "$(dirname "$0")"
PY="../../.venv/Scripts/python.exe"
BLENDER="$(PYTHONPATH=../.. "$PY" -m vsekit.env blender)"
[[ -n "$BLENDER" ]] || { echo "Blender not found (set VSEKIT_BLENDER)"; exit 1; }
step="${1:-all}"

if [[ $step == prepare || $step == all ]]; then PYTHONPATH=../.. "$PY" prepare.py; fi
if [[ $step == build   || $step == all ]]; then "$BLENDER" -b --factory-startup --python build.py | grep -E "REPORT>>|Error|Traceback" || true; fi
if [[ $step == render  || $step == all ]]; then "$BLENDER" -b projectb_devlog.blend -a | grep -E "Error|Traceback" || true; fi
if [[ $step == final   || $step == all ]]; then
  PYTHONPATH=../.. "$PY" -c "from vsekit import media as M; \
M.finalize('out/projectb_devlog_raw.mp4', 'out/projectb_devlog.mp4'); \
print(M.probe('out/projectb_devlog.mp4')['format']['duration'], M.loudness('out/projectb_devlog.mp4'))"
fi
# Preview frames without a full render:
#   "$BLENDER" -b projectb_devlog.blend --python ../../vsekit/preview.py -- out/preview 25 6 30 300 500 700
