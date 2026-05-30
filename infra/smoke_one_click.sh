#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env.production.local"
PUBLIC_BASE_URL_ARG=""
UI_URL_ARG=""
MODE="auto"
FRONTEND_STARTED=0

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: infra/smoke_one_click.sh [--local|--docker] [env_file] [public_api_url] [public_ui_url]"
  echo "Examples:"
  echo "  infra/smoke_one_click.sh --local"
  echo "  infra/smoke_one_click.sh --local .env.production.local http://127.0.0.1:8000 http://127.0.0.1:3000"
  echo "  infra/smoke_one_click.sh --docker"
  echo
  echo "When env_file is omitted, defaults to .env.production.local then .env."
  echo "UI auth is auto-injected server-side from BUYEROS_API_KEY in env / env file; no UI key input needed."
  exit 0
fi

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
NPM_CMD=""
if command -v npm >/dev/null 2>&1; then
  NPM_CMD="npm"
elif [[ -x "/usr/local/bin/npm" ]]; then
  NPM_CMD="/usr/local/bin/npm"
elif [[ -x "${REPO_ROOT}/node_modules/.bin/npm" ]]; then
  NPM_CMD="${REPO_ROOT}/node_modules/.bin/npm"
fi

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
  if [[ -n "$NPM_CMD" ]]; then
    FRONTEND_STARTED=1
    (cd "$REPO_ROOT/frontend" && BUYEROS_API_KEY="$BUYEROS_API_KEY" BUYEROS_BACKEND_URL="http://127.0.0.1:8000" "$NPM_CMD" run dev -- --hostname 127.0.0.1 --port 3000 >"$REPO_ROOT/infra/frontend-smoke-one-click.log" 2>&1 & echo $! >"$REPO_ROOT/infra/.smoke_frontend_pid")
  else
    FRONTEND_STARTED=0
    echo "npm not found: skipping local frontend boot. Backend smoke + readiness checks will run only."
  fi

  backend_pid=$(cat "$REPO_ROOT/infra/.smoke_backend_pid")
  if [[ -f "$REPO_ROOT/infra/.smoke_frontend_pid" ]]; then
    frontend_pid=$(cat "$REPO_ROOT/infra/.smoke_frontend_pid")
  fi

  trap 'echo "Stopping local services..."; [[ -n "${backend_pid:-}" ]] && kill "$backend_pid" >/dev/null 2>&1 || true; [[ -n "${frontend_pid:-}" ]] && kill "$frontend_pid" >/dev/null 2>&1 || true; rm -f "$REPO_ROOT/infra/.smoke_backend_pid" "$REPO_ROOT/infra/.smoke_frontend_pid"; exit 0' EXIT

  wait_for_url "${PUBLIC_BASE_URL}/ping"
  if [[ -n "${frontend_pid:-}" ]]; then
    wait_for_url "${UI_URL}"
  else
    echo "UI not started, skip frontend wait."
  fi
}

if [[ "$MODE" == "docker" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found. Retry with --local."
    exit 1
  fi
  FRONTEND_STARTED=1
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
if [[ "$FRONTEND_STARTED" == "1" ]] || [[ "$MODE" == "docker" ]]; then
  bash "$REPO_ROOT/infra/smoke_full.sh" "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$UI_URL"
else
  bash "$REPO_ROOT/infra/smoke_api.sh" "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
fi

echo "Smoke done: ${PUBLIC_BASE_URL} / ${UI_URL}"
