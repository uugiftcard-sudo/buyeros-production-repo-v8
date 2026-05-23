#!/bin/bash
#
# BuyerOS VPS Daily Snapshot
# 放喺 VPS: /root/daily-snapshot.sh
# Crontab: 0 2 * * * /root/daily-snapshot.sh >> /var/log/buyeros-snapshot.log 2>&1
#
# 修正原 SOP gap：
#   - 原 awk cutoff 邏輯有 bug (CreatedAt 係 ISO string，唔係 epoch)
#   - 加 set -euo pipefail
#   - 加成功 / 失敗 alert
#   - Snapshot 失敗會 retry 一次

set -euo pipefail

# ---------- Config ----------
DATE=$(date +%Y-%m-%d)
SNAPSHOT_NAME="buyeros-${DATE}"
RETENTION_DAYS=7
LOG_TAG="[buyeros-snapshot ${DATE}]"

# 由 environment 攞 (放喺 /root/.snapshot.env)
# /root/.snapshot.env 內容範例:
#   export TG_TOKEN="..."
#   export TG_ADMIN="..."
if [ -f /root/.snapshot.env ]; then
  # shellcheck disable=SC1091
  source /root/.snapshot.env
fi

: "${TG_TOKEN:?TG_TOKEN must be set}"
: "${TG_ADMIN:?TG_ADMIN must be set}"

# ---------- Helper: send Telegram ----------
notify() {
  local msg="$1"
  curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    -d "chat_id=${TG_ADMIN}" \
    -d "text=${msg}" > /dev/null || true
}

# ---------- Step 1: Find droplet ID ----------
DROPLET_ID=$(doctl compute droplet list --format ID --no-header | head -1)
if [ -z "$DROPLET_ID" ]; then
  notify "🚨 ${LOG_TAG} CANNOT find droplet ID"
  exit 1
fi
echo "${LOG_TAG} Droplet ID: ${DROPLET_ID}"

# ---------- Step 2: Snapshot (with retry) ----------
snapshot_ok=false
for attempt in 1 2; do
  echo "${LOG_TAG} Snapshot attempt ${attempt}..."
  if doctl compute droplet-action snapshot "$DROPLET_ID" \
       --snapshot-name "$SNAPSHOT_NAME" --wait; then
    snapshot_ok=true
    break
  fi
  echo "${LOG_TAG} Attempt ${attempt} failed, sleep 60s"
  sleep 60
done

if [ "$snapshot_ok" != true ]; then
  notify "🚨 ${LOG_TAG} Snapshot FAILED after 2 attempts"
  exit 1
fi

# ---------- Step 3: Cleanup old snapshots ----------
# Format: ID  Name  CreatedAt(ISO 8601)
CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)
echo "${LOG_TAG} Deleting buyeros-* snapshots older than ${CUTOFF_DATE}"

deleted_count=0
while IFS=$'\t' read -r SNAP_ID SNAP_NAME SNAP_CREATED; do
  # Only touch our own snapshots
  case "$SNAP_NAME" in
    buyeros-*) ;;
    *) continue ;;
  esac

  # Extract YYYY-MM-DD from name (more reliable than parsing CreatedAt)
  SNAP_DATE=$(echo "$SNAP_NAME" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)
  if [ -z "$SNAP_DATE" ]; then
    continue
  fi

  if [[ "$SNAP_DATE" < "$CUTOFF_DATE" ]]; then
    echo "${LOG_TAG} Deleting ${SNAP_NAME} (${SNAP_DATE})"
    doctl compute snapshot delete "$SNAP_ID" --force || true
    deleted_count=$((deleted_count + 1))
  fi
done < <(doctl compute snapshot list \
            --resource droplet \
            --format ID,Name,CreatedAt \
            --no-header | tr -s ' ' '\t')

# ---------- Step 4: Notify success ----------
notify "✅ ${LOG_TAG} Snapshot done
Name: ${SNAPSHOT_NAME}
Cleaned: ${deleted_count} old snapshots
Retention: ${RETENTION_DAYS} days"

echo "${LOG_TAG} DONE"
