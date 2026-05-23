#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="$ROOT_DIR/workspace"
SOURCE_DIR="$ROOT_DIR/../source_faces"
TARGET_CLIP="$ROOT_DIR/input/target_test_5s.mp4"

mkdir -p "$WORKSPACE/source_images" "$WORKSPACE/target_frames" "$WORKSPACE/model" "$ROOT_DIR/output"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Missing source faces directory: $SOURCE_DIR" >&2
  exit 1
fi

find "$WORKSPACE/source_images" -type f -delete
cp "$SOURCE_DIR"/* "$WORKSPACE/source_images"/

find "$WORKSPACE/target_frames" -type f -delete
ffmpeg -y -i "$TARGET_CLIP" "$WORKSPACE/target_frames/frame_%06d.png"

echo "workspace prepared: $WORKSPACE"
