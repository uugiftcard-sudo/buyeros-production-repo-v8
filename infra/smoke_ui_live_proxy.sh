#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKEND_PORT="${BUYEROS_SMOKE_BACKEND_PORT:-8010}"
FRONTEND_PORT="${BUYEROS_SMOKE_FRONTEND_PORT:-3010}"
API_KEY="${BUYEROS_SMOKE_API_KEY:-smoke-local-key}"
PYTHON_BIN="${PYTHON:-}"
NPM_BIN="${NPM:-npm}"
TMP_DIR="$(mktemp -d)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  local exit_code="$?"
  if [[ -n "${FRONTEND_PID}" ]]; then
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
    wait "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
    wait "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
  if [[ "${exit_code}" -eq 0 ]]; then
    rm -rf "${TMP_DIR}"
  else
    echo "Smoke failed. Logs preserved at ${TMP_DIR}"
  fi
}
trap cleanup EXIT

if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
  elif [[ -x "/Users/rubykan/miniconda3/bin/python" ]]; then
    PYTHON_BIN="/Users/rubykan/miniconda3/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "python executable not found. Set PYTHON=/path/to/python."
    exit 1
  fi
fi

wait_for_url() {
  local url="$1"
  local attempts="${2:-60}"
  local delay="${3:-1}"
  local i=1

  while (( i <= attempts )); do
    if curl -fsS --max-time 3 "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
    ((i += 1))
  done

  echo "Timeout waiting for ${url}"
  return 1
}

echo "Starting BuyerOS backend on 127.0.0.1:${BACKEND_PORT}"
(
  cd "${REPO_ROOT}/backend"
  BUYEROS_API_KEY="${API_KEY}" "${PYTHON_BIN}" -m uvicorn app.workflows.main:create_app --factory --host 127.0.0.1 --port "${BACKEND_PORT}" >"${TMP_DIR}/backend.log" 2>&1
) &
BACKEND_PID="$!"
wait_for_url "http://127.0.0.1:${BACKEND_PORT}/ping" 60 1

echo "Starting BuyerOS frontend on 127.0.0.1:${FRONTEND_PORT}"
(
  cd "${REPO_ROOT}/frontend"
  BUYEROS_API_KEY="${API_KEY}" BUYEROS_BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}" "${NPM_BIN}" run dev -- --hostname 127.0.0.1 --port "${FRONTEND_PORT}" >"${TMP_DIR}/frontend.log" 2>&1
) &
FRONTEND_PID="$!"
wait_for_url "http://127.0.0.1:${FRONTEND_PORT}" 90 1

echo "Running live backend-proxy UI smoke"
(
  cd "${REPO_ROOT}/frontend"
  BUYEROS_LIVE_PROXY_SMOKE=1 BUYEROS_UI_URL="http://127.0.0.1:${FRONTEND_PORT}" "${NPM_BIN}" run ui:smoke -- tests/buyeros-live-proxy.smoke.spec.ts
)

echo "BuyerOS live backend-proxy UI smoke OK"
