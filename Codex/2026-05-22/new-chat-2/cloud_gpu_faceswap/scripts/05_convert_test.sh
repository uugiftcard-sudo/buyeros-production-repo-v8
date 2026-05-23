#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FACESWAP_DIR="$ROOT_DIR/tools/faceswap"
WORKSPACE="$ROOT_DIR/workspace"
OUTPUT_DIR="$ROOT_DIR/output/converted_frames"
OUTPUT_VIDEO="$ROOT_DIR/output/faceswap_test.mp4"
TARGET_CLIP="$ROOT_DIR/input/target_test_5s.mp4"
FRAME_RATE="$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$TARGET_CLIP")"

source "$FACESWAP_DIR/.venv/bin/activate"
cd "$FACESWAP_DIR"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

python faceswap.py convert \
  -i "$WORKSPACE/target_frames" \
  -o "$OUTPUT_DIR" \
  -m "$WORKSPACE/model" \
  -c avg-color \
  -M extended \
  -w opencv

ffmpeg -y \
  -framerate "$FRAME_RATE" \
  -i "$OUTPUT_DIR/frame_%06d.png" \
  -i "$TARGET_CLIP" \
  -map 0:v:0 -map 1:a? \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 160k \
  -shortest "$OUTPUT_VIDEO"

echo "test output: $OUTPUT_VIDEO"
