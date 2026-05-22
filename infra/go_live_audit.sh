#!/usr/bin/env bash
set -uo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: infra/go_live_audit.sh <env_file> <public_base_url> [primary_ssh] [staging_ssh]"
  echo "Example: infra/go_live_audit.sh .env.production.local https://buyeros.example.com root@206.189.116.155 root@167.172.60.38"
  exit 2
fi

ENV_FILE="$1"
PUBLIC_BASE_URL="${2%/}"
PRIMARY_SSH="${3:-}"
STAGING_SSH="${4:-}"
FAILURES=0
CURL_OPTS=()
if [[ "${BUYEROS_CURL_INSECURE:-0}" == "1" ]]; then
  CURL_OPTS=(-k)
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
from pathlib import Path
import sys

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

record() {
  local name="$1"
  shift
  echo "== ${name} =="
  if "$@"; then
    echo "PASS ${name}"
  else
    echo "FAIL ${name}"
    FAILURES=$((FAILURES + 1))
  fi
  echo
}

record_optional() {
  local name="$1"
  local target="$2"
  shift 2
  echo "== ${name} =="
  if [[ -z "$target" ]]; then
    echo "SKIP ${name}: target not provided"
    echo
    return 0
  fi
  if "$@"; then
    echo "PASS ${name}"
  else
    echo "FAIL ${name}"
    FAILURES=$((FAILURES + 1))
  fi
  echo
}

record_skippable() {
  local name="$1"
  local skip_reason="$2"
  shift 2
  echo "== ${name} =="
  if [[ -n "$skip_reason" ]]; then
    echo "SKIP ${name}: ${skip_reason}"
    echo
    return 0
  fi
  if "$@"; then
    echo "PASS ${name}"
  else
    echo "FAIL ${name}"
    FAILURES=$((FAILURES + 1))
  fi
  echo
}

check_env() {
  "$PYTHON_BIN" backend/scripts/validate_env.py --env "$ENV_FILE"
}

check_compose() {
  docker compose --env-file "$ENV_FILE" config >/tmp/buyeros-go-live-compose.yml
}

check_https_ping() {
  curl ${CURL_OPTS+"${CURL_OPTS[@]}"} -fsS --max-time 10 "${PUBLIC_BASE_URL}/ping" >/dev/null
}

check_four_systems_smoke() {
  local api_key
  api_key="$(env_value BUYEROS_API_KEY)"
  bash "$(dirname "$0")/smoke_api.sh" "$PUBLIC_BASE_URL" "$api_key"
}

check_telegram_webhook_smoke() {
  local api_key secret
  api_key="$(env_value BUYEROS_API_KEY)"
  secret="$(env_value TELEGRAM_WEBHOOK_SECRET)"
  bash "$(dirname "$0")/smoke_telegram_webhook.sh" "$PUBLIC_BASE_URL" "$api_key" "$secret" 991003
}

check_telegram_token() {
  local bot_token response
  bot_token="$(env_value TELEGRAM_BOT_TOKEN)"
  response="$(curl -sS --max-time 10 "https://api.telegram.org/bot${bot_token}/getMe")" || return 1
  TELEGRAM_GET_ME_RESPONSE="$response" "$PYTHON_BIN" - <<'PY'
import json
import os
import sys

data = json.loads(os.environ["TELEGRAM_GET_ME_RESPONSE"])
if data.get("ok") is True:
    result = data.get("result") or {}
    print({"ok": True, "username": result.get("username")})
    raise SystemExit(0)
print({"ok": data.get("ok"), "description": data.get("description")})
raise SystemExit(1)
PY
}

check_primary_vps() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$PRIMARY_SSH" \
    'cd /opt/buyeros/current && docker compose -p buyeros --env-file .env ps >/dev/null'
}

check_staging_ssh() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$STAGING_SSH" 'echo staging-ssh-ok >/dev/null'
}

record "env" check_env
DOCKER_SKIP_REASON=""
if ! command -v docker >/dev/null 2>&1; then
  DOCKER_SKIP_REASON="local Docker CLI not installed; VPS compose is checked separately"
fi

record_skippable "docker compose config" "$DOCKER_SKIP_REASON" check_compose
record "https ping" check_https_ping
record "four systems smoke" check_four_systems_smoke
record "telegram webhook mock smoke" check_telegram_webhook_smoke
record "telegram bot token" check_telegram_token
record_optional "primary vps compose" "$PRIMARY_SSH" check_primary_vps
record_optional "staging ssh" "$STAGING_SSH" check_staging_ssh

if [[ "$FAILURES" -gt 0 ]]; then
  echo "Go-live audit failed: ${FAILURES} gate(s) failing."
  exit 1
fi

echo "Go-live audit OK."
