#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: infra/deploy_vps.sh <ssh_target> <remote_dir> <env_file>"
  echo "Example: infra/deploy_vps.sh root@1.2.3.4 /opt/buyeros .env.production"
  exit 1
fi

SSH_TARGET="$1"
REMOTE_DIR="$2"
ENV_FILE="$3"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

ssh "$SSH_TARGET" "mkdir -p '$REMOTE_DIR'"

rsync -az --delete \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude ".pytest_cache" \
  --exclude ".venv" \
  --exclude ".env" \
  ./ "$SSH_TARGET:$REMOTE_DIR/"

scp "$ENV_FILE" "$SSH_TARGET:$REMOTE_DIR/.env"

ssh "$SSH_TARGET" "cd '$REMOTE_DIR' && docker compose up -d --build"
ssh "$SSH_TARGET" "cd '$REMOTE_DIR' && docker compose ps"
