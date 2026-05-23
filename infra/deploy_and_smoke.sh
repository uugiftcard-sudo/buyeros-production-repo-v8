#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: infra/deploy_and_smoke.sh <ssh_target> <remote_dir> <env_file> [public_base_url] [--backup-before]"
  echo "Example staging: infra/deploy_and_smoke.sh root@167.172.60.38 /opt/buyeros .env.production.local https://staging.example.com"
  echo "Example prod:    infra/deploy_and_smoke.sh root@206.189.116.155 /opt/buyeros .env.production.local https://api.example.com --backup-before"
  exit 2
fi

SSH_TARGET="$1"
REMOTE_DIR="$2"
ENV_FILE="$3"
PUBLIC_BASE_URL_ARG="${4:-}"
BACKUP_BEFORE="0"

for arg in "${@:4}"; do
  if [[ "$arg" == "--backup-before" ]]; then
    BACKUP_BEFORE="1"
  fi
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

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

env_value() {
  local key="$1"
  "$PYTHON_BIN" - "$ENV_FILE" "$key" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
for line in path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    found, value = stripped.split("=", 1)
    if found.strip() == key:
        print(value.strip().strip('"').strip("'"))
        break
PY
}

"$PYTHON_BIN" backend/scripts/validate_env.py --env "$ENV_FILE"

PUBLIC_BASE_URL="${PUBLIC_BASE_URL_ARG:-$(env_value PUBLIC_BASE_URL)}"
BUYEROS_API_KEY="$(env_value BUYEROS_API_KEY)"

if [[ -z "$PUBLIC_BASE_URL" ]]; then
  echo "Missing public base URL. Pass it as arg 4 or set PUBLIC_BASE_URL in $ENV_FILE."
  exit 1
fi

if [[ -z "$BUYEROS_API_KEY" ]]; then
  echo "Missing BUYEROS_API_KEY in $ENV_FILE."
  exit 1
fi

if [[ "$BACKUP_BEFORE" == "1" ]]; then
  echo "== backup before deploy =="
  bash "$(dirname "$0")/backup_vps.sh" "$SSH_TARGET" "$REMOTE_DIR" "${REMOTE_DIR}-backups"
fi

wait_for_http() {
  local url="$1"
  local attempts="${2:-30}"
  local delay="${3:-3}"

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      echo "Ready: $url"
      return 0
    fi
    echo "Waiting for $url ($i/$attempts)..."
    sleep "$delay"
  done

  echo "Service did not become ready: $url"
  return 1
}

echo "== deploy =="
bash "$(dirname "$0")/deploy_vps.sh" "$SSH_TARGET" "$REMOTE_DIR" "$ENV_FILE"

echo "== wait for api =="
wait_for_http "${PUBLIC_BASE_URL%/}/ping" "${BUYEROS_DEPLOY_WAIT_ATTEMPTS:-40}" "${BUYEROS_DEPLOY_WAIT_DELAY:-3}"

echo "== smoke =="
bash "$(dirname "$0")/smoke_api.sh" "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"

echo "Deploy and smoke OK: ${SSH_TARGET} ${PUBLIC_BASE_URL}"
