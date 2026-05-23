#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FACESWAP_DIR="$ROOT_DIR/tools/faceswap"
WORKSPACE="$ROOT_DIR/workspace_full"
MODEL_DIR="$ROOT_DIR/workspace/model"
FULL_TARGET="$ROOT_DIR/input/target_normalized.mp4"
OUTPUT_DIR="$ROOT_DIR/output/full_converted_frames"
OUTPUT_VIDEO="$ROOT_DIR/output/faceswap_full.mp4"
FRAME_RATE="$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$FULL_TARGET")"

source "$FACESWAP_DIR/.venv/bin/activate"
cd "$FACESWAP_DIR"

mkdir -p "$WORKSPACE/target_frames" "$OUTPUT_DIR"
find "$WORKSPACE/target_frames" -type f -delete
find "$OUTPUT_DIR" -type f -delete

ffmpeg -y -i "$FULL_TARGET" "$WORKSPACE/target_frames/frame_%06d.png"

python faceswap.py extract \
  -i "$WORKSPACE/target_frames" \
  -o "$WORKSPACE/target_faces_extract" \
  -D s3fd \
  -A fan \
  -nm none

python faceswap.py convert \
  -i "$WORKSPACE/target_frames" \
  -o "$OUTPUT_DIR" \
  -m "$MODEL_DIR" \
  -c avg-color \
  -M extended \
  -w opencv

ffmpeg -y \
  -framerate "$FRAME_RATE" \
  -i "$OUTPUT_DIR/frame_%06d.png" \
  -i "$FULL_TARGET" \
  -map 0:v:0 -map 1:a? \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 160k \
  -shortest "$OUTPUT_VIDEO"

echo "full output: $OUTPUT_VIDEO"
