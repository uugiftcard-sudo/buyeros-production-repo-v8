#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(cd "$ROOT_DIR/.." && pwd)"
PACKAGE_PATH="$PARENT_DIR/cloud_gpu_faceswap_upload.tar.gz"

tar \
  --exclude='cloud_gpu_faceswap/cloud_gpu_faceswap' \
  --exclude='cloud_gpu_faceswap/tools' \
  --exclude='cloud_gpu_faceswap/workspace' \
  --exclude='cloud_gpu_faceswap/workspace_full' \
  --exclude='cloud_gpu_faceswap/output' \
  --exclude='*/.DS_Store' \
  -czf "$PACKAGE_PATH" \
  -C "$PARENT_DIR" \
  cloud_gpu_faceswap \
  source_faces

echo "$PACKAGE_PATH"
