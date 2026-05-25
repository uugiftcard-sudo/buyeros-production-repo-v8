#!/usr/bin/env bash
# infra/restore_test.sh
# Phase 6: Validate DB table integrity and data availability
set -euo pipefail

SUPABASE_URL="${SUPABASE_URL:-}"
SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-}"

if [[ -z "$SUPABASE_URL" || -z "$SUPABASE_SERVICE_KEY" ]]; then
  echo "ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
  exit 1
fi

PROJECT_REF="${SUPABASE_URL#https://}"
PROJECT_REF="${PROJECT_REF%.supabase.co}"

echo "=== BuyerOS Phase 6: DB Restore Test ==="
echo "Project: $PROJECT_REF"

# 1. Count agent_memory rows
echo ""
echo "[1/4] Counting agent_memory rows..."
COUNT_HEADERS="$(mktemp)"
trap 'rm -f "$COUNT_HEADERS"' EXIT
curl -s --max-time 10 \
  "https://$PROJECT_REF.supabase.co/rest/v1/agent_memory?select=id&limit=1" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Prefer: count=exact" \
  -D "$COUNT_HEADERS" \
  -o /dev/null

COUNT=$(awk -F/ 'tolower($1) ~ /^content-range:/ {print $2}' "$COUNT_HEADERS" | tr -d '\r')
echo "agent_memory rows: ${COUNT:-unknown}"

# 2. Smoke: insert test row
echo ""
echo "[2/4] Smoke: insert test row..."
TEST_KEY="restore_test_$(date +%s)"
INSERT_RESULT=$(curl -s --max-time 10 -X POST \
  "https://$PROJECT_REF.supabase.co/rest/v1/agent_memory" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d "{
    \"namespace\": [\"restore_test\"],
    \"memory_key\": \"$TEST_KEY\",
    \"content\": {\"test\": true, \"phase\": \"p6\"},
    \"created_by\": \"restore_test.sh\"
  }" 2>&1 || echo "INSERT_FAILED")

INSERT_ID=$(python3 -c 'import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, list) and data:
        print(data[0].get("id", ""))
except Exception:
    pass' <<<"$INSERT_RESULT")
if [[ -n "$INSERT_ID" ]]; then
  echo "Insert OK, id=$INSERT_ID"

  # 3. Read back
  echo ""
  echo "[3/4] Smoke: read back test row..."
  READ_BACK=$(curl -s --max-time 10 \
    "https://$PROJECT_REF.supabase.co/rest/v1/agent_memory?id=eq.$INSERT_ID&select=memory_key,content" \
    -H "apikey: $SUPABASE_SERVICE_KEY" \
    -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" 2>&1 || echo "READ_FAILED")

  if echo "$READ_BACK" | grep -q "$TEST_KEY"; then
    echo "Read back OK"
    # 4. Cleanup
    echo ""
    echo "[4/4] Cleanup test row..."
    curl -s --max-time 10 -X DELETE \
      "https://$PROJECT_REF.supabase.co/rest/v1/agent_memory?id=eq.$INSERT_ID" \
      -H "apikey: $SUPABASE_SERVICE_KEY" \
      -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" > /dev/null
    echo "Test row cleaned up"
    echo ""
    echo "RESULT: PASS - DB restore smoke passed"
  else
    echo "RESULT: FAIL - read back mismatch"
    echo "$READ_BACK"
  fi
else
  echo "RESULT: FAIL - insert failed"
  echo "$INSERT_RESULT"
fi
