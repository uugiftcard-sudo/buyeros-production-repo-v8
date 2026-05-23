#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage: infra/failover_smoke.sh <primary_url> <secondary_url> <buyeros_api_key> <max_rto_seconds>"
  echo "Example: infra/failover_smoke.sh https://api.example.com https://backup.example.com \"\$BUYEROS_API_KEY\" 300"
  exit 2
fi

PRIMARY_URL="${1%/}"
SECONDARY_URL="${2%/}"
API_KEY="$3"
MAX_RTO_SECONDS="$4"
START_TS="$(date +%s)"

echo "== primary ping =="
curl -fsS "${PRIMARY_URL}/ping" || true
echo

echo "== secondary smoke =="
bash "$(dirname "$0")/smoke_api.sh" "$SECONDARY_URL" "$API_KEY"

END_TS="$(date +%s)"
RTO=$((END_TS - START_TS))
echo "Measured RTO smoke duration: ${RTO}s"

if [[ "$RTO" -gt "$MAX_RTO_SECONDS" ]]; then
  echo "RTO exceeded: ${RTO}s > ${MAX_RTO_SECONDS}s"
  exit 1
fi

echo "Failover smoke OK."
