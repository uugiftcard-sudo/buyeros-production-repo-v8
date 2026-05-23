#!/bin/bash
#
# BuyerOS Backup Health Check
# 用途: 每日 check 3 樣嘢 (你 SOP 原本要人手 check 嘅)
#   1. GitHub Actions daily-backup workflow 跑成功？
#   2. R2 bucket 有今日嘅 .sql.gz file？
#   3. VPS snapshot 完成？
# 任何一樣 fail → Telegram alert
#
# 放邊度都得 (本機 / VPS / GitHub Actions cron)，建議放 VPS，crontab:
#   0 9 * * * /root/health-check.sh

set -euo pipefail

# ---------- Config ----------
if [ -f /root/.health-check.env ]; then
  # shellcheck disable=SC1091
  source /root/.health-check.env
fi

: "${GITHUB_TOKEN:?GITHUB_TOKEN must be set (PAT with actions:read)}"
: "${GITHUB_REPO:?GITHUB_REPO must be set, e.g. user/buyeros-backups}"
: "${R2_ACCESS_KEY:?R2_ACCESS_KEY must be set}"
: "${R2_SECRET_KEY:?R2_SECRET_KEY must be set}"
: "${R2_BUCKET:?R2_BUCKET must be set}"
: "${R2_ENDPOINT:?R2_ENDPOINT must be set}"
: "${TG_TOKEN:?TG_TOKEN must be set}"
: "${TG_ADMIN:?TG_ADMIN must be set}"

DATE=$(date +%Y-%m-%d)
LOG_TAG="[health-check ${DATE}]"
issues=()

notify() {
  curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    -d "chat_id=${TG_ADMIN}" \
    -d "text=$1" > /dev/null || true
}

# ---------- Check 1: GitHub Actions latest run status ----------
echo "${LOG_TAG} Check 1: GitHub Actions"
LATEST_RUN=$(curl -s -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/daily-backup.yml/runs?per_page=1")

CONCLUSION=$(echo "${LATEST_RUN}" | grep -oE '"conclusion":[^,]*' | head -1 | cut -d'"' -f4)
RUN_DATE=$(echo "${LATEST_RUN}" | grep -oE '"created_at":[^,]*' | head -1 | cut -d'"' -f4 | cut -dT -f1)

if [ "${CONCLUSION}" != "success" ]; then
  issues+=("❌ GitHub Actions latest run: ${CONCLUSION:-unknown} (${RUN_DATE})")
elif [ "${RUN_DATE}" != "${DATE}" ]; then
  issues+=("❌ GitHub Actions: 最近成功係 ${RUN_DATE}，唔係今日")
else
  echo "  OK: success @ ${RUN_DATE}"
fi

# ---------- Check 2: R2 today's backup file ----------
echo "${LOG_TAG} Check 2: R2 has today's file"
export AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY}"
export AWS_SECRET_ACCESS_KEY="${R2_SECRET_KEY}"
export AWS_DEFAULT_REGION=auto

TODAY_FILE=$(aws s3 ls "s3://${R2_BUCKET}/supabase-db/" \
  --endpoint-url "${R2_ENDPOINT}" 2>/dev/null | \
  awk '{print $4}' | grep "buyeros-${DATE}.sql.gz" || true)

if [ -z "${TODAY_FILE}" ]; then
  issues+=("❌ R2 冇今日 backup file (${DATE})")
else
  TODAY_SIZE=$(aws s3 ls "s3://${R2_BUCKET}/supabase-db/${TODAY_FILE}" \
    --endpoint-url "${R2_ENDPOINT}" | awk '{print $3}')
  if [ "${TODAY_SIZE}" -lt 10240 ]; then
    issues+=("❌ R2 今日 backup 太細 (${TODAY_SIZE} bytes) — 可能 corrupt")
  else
    echo "  OK: ${TODAY_FILE} (${TODAY_SIZE} bytes)"
  fi
fi

# ---------- Check 3: VPS snapshot ----------
echo "${LOG_TAG} Check 3: VPS snapshot"
TODAY_SNAPSHOT=$(doctl compute snapshot list --resource droplet \
  --format Name --no-header 2>/dev/null | \
  grep "buyeros-${DATE}" || true)

if [ -z "${TODAY_SNAPSHOT}" ]; then
  issues+=("❌ VPS 冇今日 snapshot (buyeros-${DATE})")
else
  echo "  OK: ${TODAY_SNAPSHOT}"
fi

# ---------- Summary ----------
if [ "${#issues[@]}" -eq 0 ]; then
  # 默認唔 spam，OK 嗰陣只係 log，唔 send。
  # 想每日有確認可以 uncomment 下面：
  # notify "✅ ${LOG_TAG} 3/3 checks passed"
  echo "${LOG_TAG} ALL OK"
  exit 0
fi

# 有 issue → spam Telegram
ISSUE_TEXT=$(printf "%s\n" "${issues[@]}")
notify "🚨 ${LOG_TAG} Backup health check FAILED

${ISSUE_TEXT}

Action: 即刻去 GitHub Actions 手動 trigger workflow，唔好等到聽日"

exit 1
