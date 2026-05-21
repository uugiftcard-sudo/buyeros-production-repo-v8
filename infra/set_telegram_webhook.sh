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

if [[ -n "$WEBHOOK_SECRET" ]]; then
  curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -d "url=${PUBLIC_BASE_URL}/telegram/webhook" \
    -d "secret_token=${WEBHOOK_SECRET}"
else
  curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -d "url=${PUBLIC_BASE_URL}/telegram/webhook"
fi
