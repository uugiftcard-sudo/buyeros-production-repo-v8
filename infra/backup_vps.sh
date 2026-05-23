#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: infra/backup_vps.sh <ssh_target> [remote_dir] [backup_dir]"
  echo "Example: infra/backup_vps.sh root@206.189.116.155 /opt/buyeros /opt/buyeros-backups"
  exit 2
fi

SSH_TARGET="$1"
REMOTE_DIR="${2:-/opt/buyeros}"
BACKUP_DIR="${3:-/opt/buyeros-backups}"
STAMP="$(date +%Y%m%d%H%M%S)"
ARCHIVE="buyeros-${STAMP}.tgz"
SUMMARY_DIR="${BUYEROS_OPS_SUMMARY_DIR:-$(cd "$(dirname "$0")" && pwd)/ops_runs}"
mkdir -p "$SUMMARY_DIR"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_TS="$(date +%s)"
OK=true
NOTES="Backup created"

if ! ssh "$SSH_TARGET" "set -euo pipefail; mkdir -p '$BACKUP_DIR'; cd '$REMOTE_DIR'; tar --exclude='.git' --exclude='.venv' --exclude='__pycache__' -czf '$BACKUP_DIR/$ARCHIVE' .; ls -lh '$BACKUP_DIR/$ARCHIVE'"; then
  OK=false
  NOTES="Backup failed"
fi

ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
END_TS="$(date +%s)"
DURATION=$((END_TS - START_TS))
ARCHIVE_PATH="${SSH_TARGET}:${BACKUP_DIR}/${ARCHIVE}"
SUMMARY="{\"ok\":${OK},\"action\":\"backup\",\"target\":\"${SSH_TARGET}\",\"started_at\":\"${STARTED_AT}\",\"ended_at\":\"${ENDED_AT}\",\"duration_seconds\":${DURATION},\"notes\":\"${NOTES}\",\"archive_path\":\"${ARCHIVE_PATH}\"}"
printf '%s\n' "$SUMMARY" | tee "$SUMMARY_DIR/backup-${STAMP}.json" > "$SUMMARY_DIR/backup-latest.json"
printf '%s\n' "$SUMMARY"

if [[ "$OK" != "true" ]]; then
  exit 1
fi
