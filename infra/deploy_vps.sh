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
STAMP="$(date +%Y%m%d%H%M%S)"
RELEASE_DIR="$REMOTE_DIR/releases/$STAMP"
CURRENT_LINK="$REMOTE_DIR/current"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "./.venv/bin/python" ]]; then
    PYTHON_BIN="./.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "python/python3 not found. Set PYTHON=/path/to/python."
    exit 2
  fi
fi

"$PYTHON_BIN" backend/scripts/validate_env.py --env "$ENV_FILE"

ssh "$SSH_TARGET" "
  set -euo pipefail
  if [[ -f '$REMOTE_DIR/docker-compose.yml' && ! -d '$REMOTE_DIR/releases' ]]; then
    mv '$REMOTE_DIR' '${REMOTE_DIR}.partial-$STAMP'
  fi
  mkdir -p '$RELEASE_DIR'
"

rsync -az --delete \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude ".pytest_cache" \
  --exclude ".venv" \
  --exclude ".env" \
  --exclude ".env.*" \
  --exclude "node_modules" \
  --exclude ".next" \
  --exclude "*.tsbuildinfo" \
  ./ "$SSH_TARGET:$RELEASE_DIR/"

scp "$ENV_FILE" "$SSH_TARGET:$RELEASE_DIR/.env"

ssh "$SSH_TARGET" "
  set -euo pipefail
  cd '$RELEASE_DIR'
  docker compose -p buyeros --project-directory '$RELEASE_DIR' --env-file '$RELEASE_DIR/.env' -f '$RELEASE_DIR/docker-compose.yml' config >/tmp/buyeros-compose-config.yml
  docker compose -p buyeros --project-directory '$RELEASE_DIR' --env-file '$RELEASE_DIR/.env' -f '$RELEASE_DIR/docker-compose.yml' up -d --build
  ln -sfn '$RELEASE_DIR' '$CURRENT_LINK'
  ls -1dt '$REMOTE_DIR'/releases/* 2>/dev/null | tail -n +6 | xargs -r rm -rf
  docker compose -p buyeros --project-directory '$RELEASE_DIR' --env-file '$RELEASE_DIR/.env' -f '$RELEASE_DIR/docker-compose.yml' ps
"
