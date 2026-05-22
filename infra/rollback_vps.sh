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

ssh "$SSH_TARGET" "set -euo pipefail; test -f '$BACKUP_ARCHIVE'; if [[ -d '$REMOTE_DIR' ]]; then mv '$REMOTE_DIR' '${REMOTE_DIR}.before-rollback-${RESTORE_STAMP}'; fi; mkdir -p '$REMOTE_DIR'; tar -xzf '$BACKUP_ARCHIVE' -C '$REMOTE_DIR'; cd '$REMOTE_DIR'; docker compose up -d --build; docker compose ps"

echo "Rollback completed on ${SSH_TARGET} from ${BACKUP_ARCHIVE}"
