#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: infra/smoke_24h.sh <public_base_url> <buyeros_api_key> [duration_hours] [interval_seconds]"
  echo "Example: infra/smoke_24h.sh https://api.example.com \"\$BUYEROS_API_KEY\" 24 3600"
  exit 2
fi

BASE_URL="${1%/}"
API_KEY="$2"
DURATION_HOURS="${3:-24}"
INTERVAL_SECONDS="${4:-3600}"
SUMMARY_DIR="${BUYEROS_OPS_SUMMARY_DIR:-$(cd "$(dirname "$0")" && pwd)/ops_runs}"
mkdir -p "$SUMMARY_DIR"
STAMP="$(date +%Y%m%d%H%M%S)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_TS="$(date +%s)"
END_TS=$((START_TS + DURATION_HOURS * 3600))
RUN=0
FAILURES=0

echo "24h smoke start: base=${BASE_URL} duration_hours=${DURATION_HOURS} interval_seconds=${INTERVAL_SECONDS}"

while true; do
  NOW="$(date +%s)"
  if [[ "$NOW" -ge "$END_TS" && "$RUN" -gt 0 ]]; then
    break
  fi

  RUN=$((RUN + 1))
  echo "== smoke run ${RUN} at $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
  if bash "$(dirname "$0")/smoke_api.sh" "$BASE_URL" "$API_KEY"; then
    echo "run ${RUN}: ok"
  else
    FAILURES=$((FAILURES + 1))
    echo "run ${RUN}: failed"
  fi

  NOW="$(date +%s)"
  if [[ "$NOW" -ge "$END_TS" ]]; then
    break
  fi
  sleep "$INTERVAL_SECONDS"
done

echo "24h smoke summary: runs=${RUN} failures=${FAILURES}"
ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ACTUAL_END_TS="$(date +%s)"
DURATION=$((ACTUAL_END_TS - START_TS))
OK=true

if [[ "$FAILURES" -gt 0 ]]; then
  OK=false
fi

SUMMARY="{\"ok\":${OK},\"action\":\"smoke\",\"target\":\"${BASE_URL}\",\"started_at\":\"${STARTED_AT}\",\"ended_at\":\"${ENDED_AT}\",\"duration_seconds\":${DURATION},\"notes\":\"runs=${RUN} failures=${FAILURES}\",\"checks_passed\":$((RUN - FAILURES)),\"checks_failed\":${FAILURES}}"
printf '%s\n' "$SUMMARY" | tee "$SUMMARY_DIR/smoke-${STAMP}.json" > "$SUMMARY_DIR/smoke-latest.json"
printf '%s\n' "$SUMMARY"

if [[ "$FAILURES" -gt 0 ]]; then
  exit 1
fi

echo "24h smoke OK."
