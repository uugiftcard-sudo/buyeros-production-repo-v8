#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FACESWAP_DIR="$ROOT_DIR/tools/faceswap"
WORKSPACE="$ROOT_DIR/workspace"

source "$FACESWAP_DIR/.venv/bin/activate"
cd "$FACESWAP_DIR"

rm -rf "$WORKSPACE/source_faces_extract" "$WORKSPACE/target_faces_extract"
mkdir -p "$WORKSPACE/source_faces_extract" "$WORKSPACE/target_faces_extract"

python faceswap.py extract \
  -i "$WORKSPACE/source_images" \
  -o "$WORKSPACE/source_faces_extract" \
  -D s3fd \
  -A fan \
  -nm none

python faceswap.py extract \
  -i "$WORKSPACE/target_frames" \
  -o "$WORKSPACE/target_faces_extract" \
  -D s3fd \
  -A fan \
  -nm none

echo "review these folders before training:"
echo "$WORKSPACE/source_faces_extract"
echo "$WORKSPACE/target_faces_extract"
