#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v docker >/dev/null 2>&1; then
  docker compose up -d --build frontend
else
  cd frontend
  if command -v npm >/dev/null 2>&1; then
    npm run dev
  else
    node ./node_modules/next/dist/bin/next dev
  fi
fi

