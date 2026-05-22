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

if [[ -z "$API_KEY" ]]; then
  echo "Missing BUYEROS_API_KEY. Set BUYEROS_API_KEY env or pass it as 2nd arg."
  exit 2
fi

if [[ -z "${PUBLIC_BASE_URL:-$BASE_URL}" ]]; then
  export PUBLIC_BASE_URL="${BASE_URL}"
else
  export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$BASE_URL}"
fi
export BUYEROS_API_KEY="$API_KEY"

echo "== backend smoke start =="
bash "$(dirname "$0")/smoke_api.sh" "$BASE_URL" "$API_KEY"

echo
echo "== frontend smoke start =="
curl -fsS "$UI_URL" >/dev/null
cd frontend
BUYEROS_UI_URL="$UI_URL" npm run ui:smoke

echo "Backend + UI smoke OK: ${BASE_URL} / ${UI_URL}"
