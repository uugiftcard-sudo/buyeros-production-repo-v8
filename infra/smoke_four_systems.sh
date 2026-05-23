#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: infra/smoke_four_systems.sh <public_base_url> <buyeros_api_key>"
  echo "Example: infra/smoke_four_systems.sh https://buyeros.example.com \"\$BUYEROS_API_KEY\""
  exit 2
fi

BASE_URL="${1%/}"
API_KEY="$2"
SESSION_ID="four-systems-$(date +%Y%m%d%H%M%S)"
TODAY="$(date +%Y-%m-%d)"
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
    raise SystemExit(f"Assertion failed: {expr}\n{json.dumps(data, ensure_ascii=False)[:1200]}")
PY
}

json_get() {
  local file="$1"
  local expr="$2"
  "$PYTHON_BIN" - "$file" "$expr" <<'PY'
import json
import sys

path, expr = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(eval(expr, {"data": data}))
PY
}

echo "== base readiness and three core workspaces =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${BASE_URL}/ping" | tee "$TMP_DIR/ping.json"
assert_json "$TMP_DIR/ping.json" "data.get('status') == 'ok'"
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/projects" | tee "$TMP_DIR/projects.json"
assert_json "$TMP_DIR/projects.json" "data.get('ok') is True and {'buyeros', 'cloth', 'xau'}.issubset({{'report':'cloth','commerce':'cloth','ai_team':'buyeros','ai-team':'buyeros','xau_team':'xau','xau-team':'xau','xaupromo':'xau','xau-promo':'xau','order':'cloth','orders':'cloth','reporting':'cloth','xau_promo':'xau'}.get(item.get('normalized_project_id') or item.get('memory_key') or item.get('content', {}).get('project_id') or '', item.get('normalized_project_id') or item.get('memory_key') or item.get('content', {}).get('project_id')) for item in data.get('items', [])})"
echo

echo "== task board three workspaces =="
for lane in buyeros cloth xau; do
  curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/tasks" \
    "${json_header[@]}" "${auth_header[@]}" \
    -d "{\"title\":\"Smoke task ${SESSION_ID} ${lane}\",\"lane\":\"${lane}\",\"priority\":\"P0\",\"payload\":{\"project\":\"${lane}\",\"session_id\":\"${SESSION_ID}\"}}" >"$TMP_DIR/task-${lane}.json"
assert_json "$TMP_DIR/task-${lane}.json" "data.get('ok') is True and data.get('task', {}).get('lane') == '${lane}'"
done
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/tasks?limit=100" | tee "$TMP_DIR/tasks.json"
assert_json "$TMP_DIR/tasks.json" "data.get('ok') is True and {'buyeros', 'cloth', 'xau'}.issubset({{'buyeros':'buyeros','ai_team':'buyeros','ai-team':'buyeros','report':'cloth','commerce':'cloth','order':'cloth','orders':'cloth','cloth':'cloth','xau':'xau','xau_team':'xau','xau-team':'xau','xaupromo':'xau','xau-promo':'xau'}.get(item.get('content', {}).get('lane') or '', item.get('content', {}).get('lane')) for item in data.get('items', [])})"
echo

echo "== cloth report e2e =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/reports/create" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"period\":\"daily\",\"date\":\"${TODAY}\"}" | tee "$TMP_DIR/report-create.json"
assert_json "$TMP_DIR/report-create.json" "data.get('ok') is True and data.get('report', {}).get('project_id') == 'cloth' and data.get('report', {}).get('report_id')"
REPORT_ID="$(json_get "$TMP_DIR/report-create.json" "data['report']['report_id']")"
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/reports/history?limit=10" | tee "$TMP_DIR/report-history.json"
assert_json "$TMP_DIR/report-history.json" "data.get('ok') is True and len(data.get('items', [])) >= 1"
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/reports/export" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"report_id\":\"${REPORT_ID}\",\"limit\":10}" | tee "$TMP_DIR/report-export.json"
assert_json "$TMP_DIR/report-export.json" "data.get('ok') is True and data.get('content') and 'report_id' in data.get('content')"
echo

echo "== cloth e2e =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/agents/run" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"prompt\":\"退款 991\",\"session_id\":\"${SESSION_ID}-cloth\",\"user_id\":\"smoke-cloth\"}" | tee "$TMP_DIR/cloth-refund.json"
assert_json "$TMP_DIR/cloth-refund.json" "data.get('ok') is True and '991' in data.get('reply', '')"
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/agents/run" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"prompt\":\"991 點？\",\"session_id\":\"${SESSION_ID}-cloth\",\"user_id\":\"smoke-cloth\"}" | tee "$TMP_DIR/cloth-recall.json"
assert_json "$TMP_DIR/cloth-recall.json" "data.get('ok') is True and '991' in data.get('reply', '') and '沒有找到' not in data.get('reply', '')"
echo

echo "== xau promo e2e =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/promo/campaigns" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"name\":\"Smoke XAU Promo ${SESSION_ID}\",\"offer\":\"XAU smoke offer\",\"channel\":\"telegram\",\"budget_hkd\":500,\"utm_source\":\"smoke\",\"utm_campaign\":\"${SESSION_ID}\"}" | tee "$TMP_DIR/xau-campaign.json"
assert_json "$TMP_DIR/xau-campaign.json" "data.get('ok') is True and data.get('campaign', {}).get('project_id') == 'xau' and data.get('campaign', {}).get('campaign_id')"
CAMPAIGN_ID="$(json_get "$TMP_DIR/xau-campaign.json" "data['campaign']['campaign_id']")"
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/promo/events" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"event_type\":\"conversion\",\"value_hkd\":1288,\"source\":\"smoke\",\"metadata\":{\"session_id\":\"${SESSION_ID}\"}}" | tee "$TMP_DIR/xau-event.json"
assert_json "$TMP_DIR/xau-event.json" "data.get('ok') is True and data.get('event', {}).get('event_type') == 'conversion'"
curl ${curl_opts+"${curl_opts[@]}"} -fsS "${auth_header[@]}" "${BASE_URL}/promo/metrics?campaign_id=${CAMPAIGN_ID}" | tee "$TMP_DIR/xau-metrics.json"
assert_json "$TMP_DIR/xau-metrics.json" "data.get('ok') is True and data.get('counts', {}).get('conversion', 0) >= 1 and data.get('revenue_hkd', 0) >= 1288"
echo

echo "== ai-team e2e =="
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/tasks/dispatch_plan" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"project\":\"buyeros\",\"task_type\":\"code\",\"title\":\"Smoke AI Team run_all\",\"prompt\":\"fix repo bug and record routing\",\"session_id\":\"${SESSION_ID}-ai\",\"max_steps\":2}" | tee "$TMP_DIR/ai-plan.json"
assert_json "$TMP_DIR/ai-plan.json" "data.get('ok') is True and data.get('task_id') and data.get('plan', {}).get('project') == 'buyeros'"
TASK_ID="$(json_get "$TMP_DIR/ai-plan.json" "data['task_id']")"
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/tasks/${TASK_ID}/run_all" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"session_id\":\"${SESSION_ID}-ai\",\"max_steps\":10}" | tee "$TMP_DIR/ai-run-all.json"
assert_json "$TMP_DIR/ai-run-all.json" "data.get('status') in {'completed', 'blocked', 'max_steps_exceeded'} and 'results' in data"
curl ${curl_opts+"${curl_opts[@]}"} -fsS -X POST "${BASE_URL}/memory/timeline" \
  "${json_header[@]}" "${auth_header[@]}" \
  -d "{\"project_id\":\"buyeros\",\"session_id\":\"${SESSION_ID}-ai\",\"limit\":50}" | tee "$TMP_DIR/ai-timeline.json"
assert_json "$TMP_DIR/ai-timeline.json" "data.get('ok') is True and any((item.get('namespace') or []) in [['buyeros','routing'], ['buyeros','run_all'], ['buyeros','dispatch_plans']] for item in data.get('items', []))"
echo

echo "Three workspaces smoke OK: ${SESSION_ID}"
