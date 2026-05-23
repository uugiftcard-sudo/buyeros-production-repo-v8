#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: infra/rollback_vps.sh <ssh_target> <backup_archive> [remote_dir]"
  echo "Example: infra/rollback_vps.sh root@206.189.116.155 /opt/buyeros-backups/buyeros-20260522120000.tgz /opt/buyeros"
  exit 2
fi

SSH_TARGET="$1"
BACKUP_ARCHIVE="$2"
REMOTE_DIR="${3:-/opt/buyeros}"
RESTORE_STAMP="$(date +%Y%m%d%H%M%S)"
SUMMARY_DIR="${BUYEROS_OPS_SUMMARY_DIR:-$(cd "$(dirname "$0")" && pwd)/ops_runs}"
mkdir -p "$SUMMARY_DIR"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_TS="$(date +%s)"
OK=true
NOTES="Rollback completed"

if ! ssh "$SSH_TARGET" "set -euo pipefail; test -f '$BACKUP_ARCHIVE'; if [[ -d '$REMOTE_DIR' ]]; then mv '$REMOTE_DIR' '${REMOTE_DIR}.before-rollback-${RESTORE_STAMP}'; fi; mkdir -p '$REMOTE_DIR'; tar -xzf '$BACKUP_ARCHIVE' -C '$REMOTE_DIR'; if [[ -f '$REMOTE_DIR/current/docker-compose.yml' ]]; then COMPOSE_DIR='$REMOTE_DIR/current'; elif [[ -f '$REMOTE_DIR/docker-compose.yml' ]]; then COMPOSE_DIR='$REMOTE_DIR'; else echo 'No docker-compose.yml found in rollback target or current release'; exit 1; fi; cd \"\$COMPOSE_DIR\"; docker compose up -d --build; docker compose ps"; then
  OK=false
  NOTES="Rollback failed"
fi

ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
END_TS="$(date +%s)"
DURATION=$((END_TS - START_TS))
SUMMARY="{\"ok\":${OK},\"action\":\"rollback\",\"target\":\"${SSH_TARGET}\",\"started_at\":\"${STARTED_AT}\",\"ended_at\":\"${ENDED_AT}\",\"duration_seconds\":${DURATION},\"notes\":\"${NOTES}\",\"rollback_source\":\"${BACKUP_ARCHIVE}\"}"
printf '%s\n' "$SUMMARY" | tee "$SUMMARY_DIR/rollback-${RESTORE_STAMP}.json" > "$SUMMARY_DIR/rollback-latest.json"
printf '%s\n' "$SUMMARY"

if [[ "$OK" != "true" ]]; then
  exit 1
fi
