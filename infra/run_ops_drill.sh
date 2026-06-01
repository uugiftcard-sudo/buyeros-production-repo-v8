#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage: infra/run_ops_drill.sh <env_file> <primary_url> <secondary_url> <primary_ssh> [remote_dir] [backup_dir] [max_rto_seconds]"
  echo "Example: infra/run_ops_drill.sh .env.production.local https://primary.example.com https://secondary.example.com root@1.2.3.4"
  exit 2
fi

ENV_FILE="$1"
PRIMARY_URL="${2%/}"
SECONDARY_URL="${3%/}"
PRIMARY_SSH="$4"
REMOTE_DIR="${5:-/opt/buyeros}"
BACKUP_DIR="${6:-/opt/buyeros-backups}"
MAX_RTO_SECONDS="${7:-300}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUMMARY_DIR="${BUYEROS_OPS_SUMMARY_DIR:-$SCRIPT_DIR/ops_runs}"
mkdir -p "$SUMMARY_DIR"
PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "python/python3 not found. Set PYTHON=/path/to/python."
    exit 2
  fi
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${BUYEROS_API_KEY:-}" ]]; then
  echo "BUYEROS_API_KEY missing in env file"
  exit 2
fi

echo "== backup primary =="
BACKUP_STATUS=0
BUYEROS_OPS_SUMMARY_DIR="$SUMMARY_DIR" bash "$SCRIPT_DIR/backup_vps.sh" "$PRIMARY_SSH" "$REMOTE_DIR" "$BACKUP_DIR" || BACKUP_STATUS=$?

echo "== failover smoke =="
FAILOVER_STATUS=0
BUYEROS_OPS_SUMMARY_DIR="$SUMMARY_DIR" bash "$SCRIPT_DIR/failover_smoke.sh" "$PRIMARY_URL" "$SECONDARY_URL" "$BUYEROS_API_KEY" "$MAX_RTO_SECONDS" || FAILOVER_STATUS=$?

echo "== sync summaries to primary current release =="
ssh "$PRIMARY_SSH" "mkdir -p '$REMOTE_DIR/current/infra/ops_runs'"
rsync -az "$SUMMARY_DIR/" "$PRIMARY_SSH:$REMOTE_DIR/current/infra/ops_runs/"

echo "== verify production ops status =="
curl -fsS -H "Authorization: Bearer ${BUYEROS_API_KEY}" "${PRIMARY_URL}/ops/status" | "$PYTHON_BIN" -m json.tool

if [[ "$BACKUP_STATUS" -ne 0 || "$FAILOVER_STATUS" -ne 0 ]]; then
  echo "Ops drill completed with failures: backup=${BACKUP_STATUS} failover=${FAILOVER_STATUS}. Summaries were synced."
  exit 1
fi

echo "Ops drill OK: summaries synced to ${PRIMARY_SSH}:${REMOTE_DIR}/current/infra/ops_runs"
