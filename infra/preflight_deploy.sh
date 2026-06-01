#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: infra/preflight_deploy.sh <env_file>"
  exit 2
fi

ENV_FILE="$1"

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "./.venv/bin/python" ]]; then
    PYTHON_BIN="./.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "python/python3 not found. Set PYTHON=/path/to/python."
    exit 2
  fi
fi

"$PYTHON_BIN" backend/scripts/validate_env.py --env "$ENV_FILE"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI is not installed on this machine."
  exit 1
fi

docker compose config >/dev/null
echo "Preflight OK."
