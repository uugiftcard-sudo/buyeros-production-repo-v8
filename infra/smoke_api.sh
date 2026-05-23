#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: infra/smoke_api.sh <public_base_url> <buyeros_api_key>"
  echo "Example: infra/smoke_api.sh https://buyeros.example.com \"\$BUYEROS_API_KEY\""
  exit 2
fi

BASE_URL="${1%/}"
API_KEY="$2"
SESSION_ID="smoke-$(date +%Y%m%d%H%M%S)"
TASK_ID="task-${SESSION_ID}"
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

auth_header=(-H "Authorization: Bearer ${API_KEY}")
json_header=(-H "Content-Type: application/json")
curl_opts=()
if [[ "${BUYEROS_CURL_INSECURE:-0}" == "1" ]]; then
  curl_opts=(-k)
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
    raise SystemExit(f"Assertion failed: {expr}\n{json.dumps(data, ensure_ascii=False)[:1000]}")
PY
}

echo "== ping =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${BASE_URL}/ping" | tee "$TMP_DIR/ping.json"
assert_json "$TMP_DIR/ping.json" "data.get('status') == 'ok'"
echo

echo "== readiness =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${BASE_URL}/health/ready" | tee "$TMP_DIR/ready.json"
assert_json "$TMP_DIR/ready.json" "data.get('ok') is True"
echo

echo "== providers =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/providers" | tee "$TMP_DIR/providers.json"
assert_json "$TMP_DIR/providers.json" "data.get('ok') is True and len(data.get('providers', [])) >= 1"
echo

echo "== projects =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/projects" | tee "$TMP_DIR/projects.json"
assert_json "$TMP_DIR/projects.json" "data.get('ok') is True and len(data.get('items', [])) >= 1"
echo

echo "== context write =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/context/write" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"source_provider\":\"smoke\",\"session_id\":\"${SESSION_ID}\",\"task_id\":\"${TASK_ID}\",\"content\":{\"text\":\"退款 991 已處理\"},\"summary\":\"smoke 退款 991 已處理\"}" | tee "$TMP_DIR/write.json"
assert_json "$TMP_DIR/write.json" "data.get('ok') is True"
echo

echo "== context search =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/context/search" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"query\":\"991\",\"session_id\":\"${SESSION_ID}\",\"limit\":5}" | tee "$TMP_DIR/search.json"
assert_json "$TMP_DIR/search.json" "data.get('ok') is True and len(data.get('items', [])) >= 1"
echo

echo "== context session =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/context/session/${SESSION_ID}" | tee "$TMP_DIR/session.json"
assert_json "$TMP_DIR/session.json" "data.get('ok') is True and len(data.get('items', [])) >= 1"
echo

echo "== agents run refund =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/agents/run" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"prompt\":\"退款 991\",\"session_id\":\"${SESSION_ID}\",\"user_id\":\"smoke\"}" | tee "$TMP_DIR/agent-refund.json"
assert_json "$TMP_DIR/agent-refund.json" "data.get('ok') is True and '991' in data.get('reply', '')"
echo

echo "== agents run recall =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/agents/run" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"prompt\":\"991 點？\",\"session_id\":\"${SESSION_ID}\",\"user_id\":\"smoke\"}" | tee "$TMP_DIR/agent-recall.json"
assert_json "$TMP_DIR/agent-recall.json" "data.get('ok') is True and '991' in data.get('reply', '') and '沒有找到' not in data.get('reply', '')"
echo

echo "== dispatch plan =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/tasks/dispatch_plan" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"project\":\"cloth\",\"task_type\":\"refund\",\"title\":\"Smoke refund run_all\",\"prompt\":\"退款 991\",\"session_id\":\"${SESSION_ID}\",\"max_steps\":2}" | tee "$TMP_DIR/dispatch-plan.json"
assert_json "$TMP_DIR/dispatch-plan.json" "data.get('ok') is True and data.get('task_id')"
DISPATCH_TASK_ID="$("$PYTHON_BIN" - "$TMP_DIR/dispatch-plan.json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    print(json.load(fh)["task_id"])
PY
)"
echo

echo "== run all =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/tasks/${DISPATCH_TASK_ID}/run_all" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"session_id\":\"${SESSION_ID}\",\"max_steps\":10}" | tee "$TMP_DIR/run-all.json"
assert_json "$TMP_DIR/run-all.json" "data.get('status') in {'completed', 'blocked', 'max_steps_exceeded'} and 'results' in data"
assert_json "$TMP_DIR/run-all.json" "all('991' in ((item.get('result') or {}).get('reply') or '991') for item in data.get('results', []))"
echo

echo "== memory timeline =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/memory/timeline" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"project_id\":\"cloth\",\"session_id\":\"${SESSION_ID}\",\"limit\":50}" | tee "$TMP_DIR/timeline.json"
assert_json "$TMP_DIR/timeline.json" "data.get('ok') is True and len(data.get('items', [])) >= 1"
echo

SKIP_FOUR_SYSTEMS_SMOKE="${BUYEROS_SKIP_FOUR_SYSTEMS_SMOKE:-${BUYEROS_SKIP_THREE_SYSTEMS_SMOKE:-0}}"
if [[ "$SKIP_FOUR_SYSTEMS_SMOKE" != "1" ]]; then
  echo "== three workspaces e2e =="
  bash "$(dirname "$0")/smoke_four_systems.sh" "$BASE_URL" "$API_KEY"
  echo
fi

echo "Smoke OK: ${SESSION_ID}"
