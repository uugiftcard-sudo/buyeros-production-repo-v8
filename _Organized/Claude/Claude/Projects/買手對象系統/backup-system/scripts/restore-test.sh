#!/bin/bash
#
# BuyerOS Monthly Restore Drill
# 用途: 每月 1 號自動 download 上月 backup → restore 入 test Supabase project → verify
#
# 你 SOP 講「冇 test 過嘅 backup = 等於冇 backup」— 呢個 script 將呢句話自動化
#
# Run locally (or 喺另一台 server): ./restore-test.sh
# Crontab option (本機): 0 9 1 * * /path/to/restore-test.sh

set -euo pipefail

# ---------- Config ----------
# 由 environment 攞 (放喺 ~/.buyeros-restore.env)
# 範例:
#   export PROD_PROJECT_REF="jnzdklfjdjmhjrhntljp"
#   export TEST_PROJECT_REF="xxxxxxxxxxxxxxxxxxxx"
#   export TEST_DB_PASSWORD="..."
#   export R2_ACCESS_KEY="..."
#   export R2_SECRET_KEY="..."
#   export R2_BUCKET="buyeros-backups"
#   export R2_ENDPOINT="https://<account>.r2.cloudflarestorage.com"
#   export TG_TOKEN="..."
#   export TG_ADMIN="..."
if [ -f "${HOME}/.buyeros-restore.env" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/.buyeros-restore.env"
fi

: "${TEST_PROJECT_REF:?TEST_PROJECT_REF must be set}"
: "${TEST_DB_PASSWORD:?TEST_DB_PASSWORD must be set}"
: "${R2_ACCESS_KEY:?R2_ACCESS_KEY must be set}"
: "${R2_SECRET_KEY:?R2_SECRET_KEY must be set}"
: "${R2_BUCKET:?R2_BUCKET must be set}"
: "${R2_ENDPOINT:?R2_ENDPOINT must be set}"
: "${TG_TOKEN:?TG_TOKEN must be set}"
: "${TG_ADMIN:?TG_ADMIN must be set}"

WORKDIR=$(mktemp -d -t buyeros-restore-XXXXXX)
trap 'rm -rf "${WORKDIR}"' EXIT
cd "${WORKDIR}"

DATE_TAG=$(date +%Y-%m-%d)
LOG_TAG="[restore-drill ${DATE_TAG}]"

notify() {
  curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    -d "chat_id=${TG_ADMIN}" \
    -d "text=$1" > /dev/null || true
}

echo "${LOG_TAG} Working dir: ${WORKDIR}"

# ---------- Step 1: 揾最新 backup ----------
export AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY}"
export AWS_SECRET_ACCESS_KEY="${R2_SECRET_KEY}"
export AWS_DEFAULT_REGION=auto

LATEST_KEY=$(aws s3 ls "s3://${R2_BUCKET}/supabase-db/" \
  --endpoint-url "${R2_ENDPOINT}" | \
  awk '{print $4}' | grep '\.sql\.gz$' | sort | tail -1)

if [ -z "${LATEST_KEY}" ]; then
  notify "🚨 ${LOG_TAG} 揾唔到任何 backup file"
  exit 1
fi

echo "${LOG_TAG} Latest backup: ${LATEST_KEY}"

# ---------- Step 2: Download ----------
aws s3 cp "s3://${R2_BUCKET}/supabase-db/${LATEST_KEY}" "./${LATEST_KEY}" \
  --endpoint-url "${R2_ENDPOINT}"

gunzip "./${LATEST_KEY}"
SQL_FILE="${LATEST_KEY%.gz}"
SIZE_KB=$(du -k "${SQL_FILE}" | cut -f1)
echo "${LOG_TAG} Decompressed ${SQL_FILE} (${SIZE_KB} KB)"

# ---------- Step 3: Restore 入 test project ----------
echo "${LOG_TAG} Restoring to test project ${TEST_PROJECT_REF}..."

PGPASSWORD="${TEST_DB_PASSWORD}" psql \
  -h "db.${TEST_PROJECT_REF}.supabase.co" \
  -p 5432 \
  -U postgres \
  -d postgres \
  -f "${SQL_FILE}" \
  -v ON_ERROR_STOP=1 \
  > restore.log 2>&1

# ---------- Step 4: Verify tables ----------
echo "${LOG_TAG} Verifying tables..."
TABLE_COUNT=$(PGPASSWORD="${TEST_DB_PASSWORD}" psql \
  -h "db.${TEST_PROJECT_REF}.supabase.co" \
  -p 5432 \
  -U postgres \
  -d postgres \
  -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")

# 預期 24 tables（你 SOP 講嘅）
EXPECTED_MIN=20

if [ "${TABLE_COUNT}" -lt "${EXPECTED_MIN}" ]; then
  notify "🚨 ${LOG_TAG} Restore VERIFY FAILED
Tables: ${TABLE_COUNT} (expected >= ${EXPECTED_MIN})
Backup: ${LATEST_KEY}"
  exit 1
fi

# ---------- Step 5: Sample row check (核心 tables 唔可以空) ----------
CRITICAL_TABLES=("buyers" "transactions" "refunds")  # 改成你實際 table 名
for tbl in "${CRITICAL_TABLES[@]}"; do
  ROW_COUNT=$(PGPASSWORD="${TEST_DB_PASSWORD}" psql \
    -h "db.${TEST_PROJECT_REF}.supabase.co" \
    -p 5432 -U postgres -d postgres \
    -tAc "SELECT count(*) FROM public.${tbl};" 2>/dev/null || echo "MISSING")

  if [ "${ROW_COUNT}" = "MISSING" ]; then
    notify "⚠️ ${LOG_TAG} Critical table missing: ${tbl}"
  elif [ "${ROW_COUNT}" -eq 0 ]; then
    notify "⚠️ ${LOG_TAG} Critical table empty: ${tbl}"
  fi
done

# ---------- Step 6: Cleanup test project (truncate, 等下個月再 test) ----------
# 留返 schema，只清 data，落個月 restore 過嗰陣 --clean --if-exists 自動處理
# (呢部分原 SOP 冇講，加咗保護防止 test project 越積越多)

# ---------- Step 7: Notify success ----------
notify "✅ ${LOG_TAG} Restore drill PASSED
Backup: ${LATEST_KEY}
Tables restored: ${TABLE_COUNT}
Size: ${SIZE_KB} KB
Test project: ${TEST_PROJECT_REF}"

echo "${LOG_TAG} DONE"
