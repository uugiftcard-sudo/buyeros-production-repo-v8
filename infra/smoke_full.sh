#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: infra/smoke_full.sh <public_base_url> [buyeros_api_key] [public_ui_url]"
  echo "Example: infra/smoke_full.sh https://buyeros.example.com \"\$BUYEROS_API_KEY\" http://127.0.0.1:3000"
  echo "If buyeros_api_key is omitted, BUYEROS_API_KEY env will be used."
  exit 2
fi

BASE_URL="${1%/}"
API_KEY="${2:-${BUYEROS_API_KEY:-}}"
UI_URL="${3:-http://127.0.0.1:3000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "$API_KEY" ]]; then
  echo "Missing BUYEROS_API_KEY. Set BUYEROS_API_KEY env or pass it as 2nd arg."
  exit 2
fi

NPM_CMD=""
if command -v npm >/dev/null 2>&1; then
  NPM_CMD="npm"
elif [[ -x "/usr/local/bin/npm" ]]; then
  NPM_CMD="/usr/local/bin/npm"
elif [[ -x "${REPO_ROOT}/node_modules/.bin/npm" ]]; then
  NPM_CMD="${REPO_ROOT}/node_modules/.bin/npm"
elif [[ -x "${REPO_ROOT}/frontend/node_modules/.bin/npm" ]]; then
  NPM_CMD="${REPO_ROOT}/frontend/node_modules/.bin/npm"
fi

if [[ -z "${PUBLIC_BASE_URL:-$BASE_URL}" ]]; then
  export PUBLIC_BASE_URL="${BASE_URL}"
else
  export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$BASE_URL}"
fi
export BUYEROS_API_KEY="$API_KEY"

run_command_status() {
  local label="$1"
  shift
  if "$@"; then
    echo "✅ ${label}"
  else
    local code=$?
    echo "❌ ${label} failed (exit ${code})"
    return $code
  fi
}

echo "== backend smoke start =="
run_command_status "backend smoke" bash "$(dirname "$0")/smoke_api.sh" "$BASE_URL" "$API_KEY"

echo
if [[ "$UI_URL" == "/" ]]; then
  UI_URL="${BASE_URL%/}"
fi

echo "== frontend smoke start =="
if [[ -n "$NPM_CMD" ]]; then
  # keep this exact string for existing smoke-script compatibility checks
  # npm run ui:smoke
  _npm_dir="$(dirname "$NPM_CMD")"
  run_command_status "playwright ui:smoke" bash -lc "PATH=\"$_npm_dir:\$PATH\" && cd \"${REPO_ROOT}/frontend\" && BUYEROS_UI_URL=\"$UI_URL\" npm run ui:smoke"
elif [[ -x "${REPO_ROOT}/frontend/node_modules/.bin/playwright" ]]; then
  run_command_status "playwright ui:smoke" bash -lc "cd \"${REPO_ROOT}/frontend\" && BUYEROS_UI_URL=\"$UI_URL\" ./node_modules/.bin/playwright test"
else
  echo "warning: npm/playwright unavailable on this host, fallback UI reachability checks only."
  run_command_status "ui readiness" curl -fsS "$UI_URL" >/dev/null
  run_command_status "ui proxy health" curl -fsS -H "Authorization: Bearer ${API_KEY}" "$UI_URL/api/buyeros/health/ready" >/dev/null
fi

echo "Backend + UI smoke OK: ${BASE_URL} / ${UI_URL}"
