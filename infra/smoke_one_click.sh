#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env.production.local"
PUBLIC_BASE_URL_ARG=""
UI_URL_ARG=""
MODE="auto"

for arg in "$@"; do
  case "$arg" in
    --local)
      MODE="local"
      ;;
    --docker)
      MODE="docker"
      ;;
    http://*|https://*)
      if [[ -z "$PUBLIC_BASE_URL_ARG" ]]; then
        PUBLIC_BASE_URL_ARG="$arg"
      else
        UI_URL_ARG="$arg"
      fi
      ;;
    *)
      if [[ -z "$ENV_FILE" || "$ENV_FILE" == ".env.production.local" ]]; then
        ENV_FILE="$arg"
      elif [[ -z "$PUBLIC_BASE_URL_ARG" ]]; then
        PUBLIC_BASE_URL_ARG="$arg"
      elif [[ -z "$UI_URL_ARG" ]]; then
        UI_URL_ARG="$arg"
      fi
      ;;
  esac
done

if [[ -z "$PUBLIC_BASE_URL_ARG" ]]; then
  PUBLIC_BASE_URL_ARG="http://127.0.0.1:8000"
fi
if [[ -z "$UI_URL_ARG" ]]; then
  UI_URL_ARG="http://127.0.0.1:3000"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$REPO_ROOT/.env" ]]; then
    ENV_FILE="$REPO_ROOT/.env"
  else
    echo "Missing env file: $ENV_FILE"
    exit 1
  fi
fi

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  else
    echo "python executable not found. Set PYTHON or install python3."
    exit 2
  fi
fi

env_value() {
  local key="$1"
  "$PYTHON_BIN" - "$ENV_FILE" "$key" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
for line in path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    name, value = stripped.split("=", 1)
    if name.strip() == key:
        print(value.strip().strip('"').strip("'"))
        break
PY
}

BUYEROS_API_KEY="${BUYEROS_API_KEY:-$(env_value BUYEROS_API_KEY)}"
if [[ -z "$BUYEROS_API_KEY" ]]; then
  echo "BUYEROS_API_KEY not found in env file: $ENV_FILE"
  exit 1
fi

PUBLIC_BASE_URL="${PUBLIC_BASE_URL_ARG}"
if [[ -z "$PUBLIC_BASE_URL" ]]; then
  PUBLIC_BASE_URL="$(env_value PUBLIC_BASE_URL || true)"
  PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://127.0.0.1:8000}"
fi
UI_URL="${UI_URL_ARG}"
UI_URL="${UI_URL:-http://127.0.0.1:3000}"

wait_for_url() {
  local url="$1"
  local retry="${2:-40}"
  local delay="${3:-3}"
  local i=1

  while (( i <= retry )); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
      return 0
    fi
    echo "Waiting for $url ($i/$retry)..."
    sleep "$delay"
    ((i += 1))
  done

  echo "Timeout waiting for $url"
  return 1
}

launch_local_services() {
  echo "== start local services =="
  "$PYTHON_BIN" "$REPO_ROOT/backend/scripts/validate_env.py" --env "$ENV_FILE" || true

  backend_pid=""
  frontend_pid=""

  (cd "$REPO_ROOT/backend" && BUYEROS_API_KEY="$BUYEROS_API_KEY" "$REPO_ROOT/.venv/bin/uvicorn" app.workflows.main:create_app --factory --host 127.0.0.1 --port 8000 >"$REPO_ROOT/infra/backend-smoke-one-click.log" 2>&1 & echo $! >"$REPO_ROOT/infra/.smoke_backend_pid")
  (cd "$REPO_ROOT/frontend" && BUYEROS_API_KEY="$BUYEROS_API_KEY" BUYEROS_BACKEND_URL="http://127.0.0.1:8000" npm run dev -- --hostname 127.0.0.1 --port 3000 >"$REPO_ROOT/infra/frontend-smoke-one-click.log" 2>&1 & echo $! >"$REPO_ROOT/infra/.smoke_frontend_pid")

  backend_pid=$(cat "$REPO_ROOT/infra/.smoke_backend_pid")
  frontend_pid=$(cat "$REPO_ROOT/infra/.smoke_frontend_pid")

  trap 'echo "Stopping local services..."; kill "$backend_pid" "$frontend_pid" >/dev/null 2>&1 || true; rm -f "$REPO_ROOT/infra/.smoke_backend_pid" "$REPO_ROOT/infra/.smoke_frontend_pid"; exit 0' EXIT

  wait_for_url "${PUBLIC_BASE_URL}/ping"
  wait_for_url "${UI_URL}"
}

if [[ "$MODE" == "docker" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found. Retry with --local."
    exit 1
  fi
  echo "== run docker compose =="
  cd "$REPO_ROOT" && docker compose up -d --build
  wait_for_url "${PUBLIC_BASE_URL}/ping" 60 2
elif [[ "$MODE" == "local" ]]; then
  launch_local_services
else
  if command -v docker >/dev/null 2>&1; then
    echo "docker found; using docker mode. Use --local to force local process mode."
    cd "$REPO_ROOT" && docker compose up -d --build
    wait_for_url "${PUBLIC_BASE_URL}/ping" 60 2
  else
    launch_local_services
  fi
fi

echo "== run one-click smoke =="
bash "$REPO_ROOT/infra/smoke_full.sh" "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$UI_URL"

echo "Smoke done: ${PUBLIC_BASE_URL} / ${UI_URL}"
