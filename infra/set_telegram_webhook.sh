#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: infra/set_telegram_webhook.sh <telegram_bot_token> <public_base_url> [webhook_secret]"
  echo "Example: infra/set_telegram_webhook.sh 123:abc https://buyeros.example.com my-secret"
  exit 1
fi

BOT_TOKEN="$1"
PUBLIC_BASE_URL="${2%/}"
WEBHOOK_SECRET="${3:-}"

echo "== validate bot token =="
GET_ME_RESPONSE="$(curl -sS "https://api.telegram.org/bot${BOT_TOKEN}/getMe")"
if ! printf '%s' "$GET_ME_RESPONSE" | python3 -c 'import json,sys; raise SystemExit(0 if json.load(sys.stdin).get("ok") is True else 1)' >/dev/null 2>&1; then
  printf '%s\n' "$GET_ME_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print({"ok": d.get("ok"), "description": d.get("description")})'
  echo "Telegram bot token is not accepted by Telegram. Refresh TELEGRAM_BOT_TOKEN from BotFather and retry."
  exit 1
fi

echo "== set webhook =="
if [[ -n "$WEBHOOK_SECRET" ]]; then
  curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -d "url=${PUBLIC_BASE_URL}/telegram/webhook" \
    -d "secret_token=${WEBHOOK_SECRET}"
else
  curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -d "url=${PUBLIC_BASE_URL}/telegram/webhook"
fi
