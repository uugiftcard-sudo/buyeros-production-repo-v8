#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: infra/smoke_telegram_webhook.sh <public_base_url> <buyeros_api_key> <telegram_webhook_secret> [chat_id]"
  echo "Example: infra/smoke_telegram_webhook.sh https://buyeros.example.com \"\$BUYEROS_API_KEY\" \"\$TELEGRAM_WEBHOOK_SECRET\" 991001"
  exit 2
fi

BASE_URL="${1%/}"
API_KEY="$2"
WEBHOOK_SECRET="$3"
CHAT_ID="${4:-991001}"
SESSION_ID="${CHAT_ID}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif [[ -x "./.venv/bin/python" ]]; then
    PYTHON_BIN="./.venv/bin/python"
  else
    echo "python/python3 not found. Set PYTHON=/path/to/python."
    exit 2
  fi
fi

assert_json() {
  local file="$1"
  local expr="$2"
  "$PYTHON_BIN" - "$file" "$expr" <<'PY'
import json
import sys

path, expr = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
if not eval(expr, {"data": data}):
    raise SystemExit(f"Assertion failed: {expr}\n{json.dumps(data, ensure_ascii=False)[:1200]}")
PY
}

auth_header=(-H "Authorization: Bearer ${API_KEY}")
json_header=(-H "Content-Type: application/json")
telegram_secret_header=(-H "X-Telegram-Bot-Api-Secret-Token: ${WEBHOOK_SECRET}")
curl_opts=()
if [[ "${BUYEROS_CURL_INSECURE:-0}" == "1" ]]; then
  curl_opts=(-k)
fi

echo "== telegram webhook refund =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/telegram/webhook" \
  "${json_header[@]}" "${telegram_secret_header[@]}" \
  -d "{\"update_id\":$(date +%s),\"message\":{\"chat\":{\"id\":${CHAT_ID}},\"text\":\"退款 991\"}}" | tee "$TMP_DIR/refund.json"
assert_json "$TMP_DIR/refund.json" "data.get('ok') is True"

echo "== telegram webhook recall =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/telegram/webhook" \
  "${json_header[@]}" "${telegram_secret_header[@]}" \
  -d "{\"update_id\":$(date +%s),\"message\":{\"chat\":{\"id\":${CHAT_ID}},\"text\":\"991 點？\"}}" | tee "$TMP_DIR/recall.json"
assert_json "$TMP_DIR/recall.json" "data.get('ok') is True"

echo "== verify shared context session =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/context/session/${SESSION_ID}" | tee "$TMP_DIR/session.json"
assert_json "$TMP_DIR/session.json" "data.get('ok') is True and any('991' in str(item.get('content', {})) for item in data.get('items', []))"

echo "Telegram webhook smoke OK: chat_id=${CHAT_ID}"
