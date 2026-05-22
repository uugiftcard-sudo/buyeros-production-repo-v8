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

ssh "$SSH_TARGET" "set -euo pipefail; mkdir -p '$BACKUP_DIR'; cd '$REMOTE_DIR'; tar --exclude='.git' --exclude='.venv' --exclude='__pycache__' -czf '$BACKUP_DIR/$ARCHIVE' .; ls -lh '$BACKUP_DIR/$ARCHIVE'"

echo "Backup created: ${SSH_TARGET}:${BACKUP_DIR}/${ARCHIVE}"
