#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FACESWAP_DIR="$ROOT_DIR/tools/faceswap"
WORKSPACE="$ROOT_DIR/workspace"
ITERATIONS="${ITERATIONS:-5000}"

source "$FACESWAP_DIR/.venv/bin/activate"
cd "$FACESWAP_DIR"

python faceswap.py train \
  -A "$WORKSPACE/source_faces_extract" \
  -B "$WORKSPACE/target_faces_extract" \
  -m "$WORKSPACE/model" \
  -t original \
  -bs 8 \
  -it "$ITERATIONS" \
  -s 250

echo "training preview complete: $WORKSPACE/model"
