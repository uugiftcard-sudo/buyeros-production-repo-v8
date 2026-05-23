#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$ROOT_DIR/tools"
FACESWAP_DIR="$TOOLS_DIR/faceswap"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This setup script must run on an Ubuntu NVIDIA GPU VM, not on this Mac."
  echo "Upload cloud_gpu_faceswap_upload.tar.gz to the VM, unpack it, then run this script there."
  exit 1
fi

mkdir -p "$TOOLS_DIR"

sudo apt-get update
sudo apt-get install -y git ffmpeg python3 python3-venv python3-pip build-essential

if [ ! -d "$FACESWAP_DIR/.git" ]; then
  git clone https://github.com/deepfakes/faceswap.git "$FACESWAP_DIR"
fi

cd "$FACESWAP_DIR"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements/requirements_nvidia.txt

python faceswap.py -h >/dev/null
echo "faceswap setup complete: $FACESWAP_DIR"
