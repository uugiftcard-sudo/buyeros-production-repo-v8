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
SUMMARY_DIR="${BUYEROS_OPS_SUMMARY_DIR:-$(cd "$(dirname "$0")" && pwd)/ops_runs}"
mkdir -p "$SUMMARY_DIR"
STAMP="$(date +%Y%m%d%H%M%S)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_TS="$(date +%s)"
OK=true
NOTES="Failover smoke OK"
LAST_BACKUP_AT=""
RPO_SECONDS=0
if [[ -f "$SUMMARY_DIR/backup-latest.json" ]]; then
  LAST_BACKUP_AT="$(python3 - "$SUMMARY_DIR/backup-latest.json" <<'PY' || true
import json, sys
from datetime import datetime
data = json.load(open(sys.argv[1], encoding="utf-8"))
print(data.get("ended_at") or "")
PY
)"
  if [[ -n "$LAST_BACKUP_AT" ]]; then
    LAST_BACKUP_TS="$(python3 - "$LAST_BACKUP_AT" <<'PY' || true
import sys
from datetime import datetime
raw = sys.argv[1].replace("Z", "+00:00")
print(int(datetime.fromisoformat(raw).timestamp()))
PY
)"
    if [[ -n "${LAST_BACKUP_TS:-}" ]]; then
      RPO_SECONDS=$((START_TS - LAST_BACKUP_TS))
    fi
  fi
fi

echo "== primary ping =="
curl -fsS "${PRIMARY_URL}/ping" || true
echo

echo "== secondary smoke =="
if ! bash "$(dirname "$0")/smoke_api.sh" "$SECONDARY_URL" "$API_KEY"; then
  OK=false
  NOTES="Secondary smoke failed"
fi

END_TS="$(date +%s)"
ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RTO=$((END_TS - START_TS))
echo "Measured RTO smoke duration: ${RTO}s"

if [[ "$RTO" -gt "$MAX_RTO_SECONDS" ]]; then
  echo "RTO exceeded: ${RTO}s > ${MAX_RTO_SECONDS}s"
  OK=false
  NOTES="RTO exceeded"
fi

SUMMARY="{\"ok\":${OK},\"action\":\"failover\",\"target\":\"${SECONDARY_URL}\",\"started_at\":\"${STARTED_AT}\",\"ended_at\":\"${ENDED_AT}\",\"duration_seconds\":${RTO},\"notes\":\"${NOTES}\",\"rto_seconds\":${RTO},\"last_backup_at\":\"${LAST_BACKUP_AT}\",\"rpo_seconds\":${RPO_SECONDS}}"
printf '%s\n' "$SUMMARY" | tee "$SUMMARY_DIR/failover-${STAMP}.json" > "$SUMMARY_DIR/failover-latest.json"
printf '%s\n' "$SUMMARY"

if [[ "$OK" != "true" ]]; then
  exit 1
fi
