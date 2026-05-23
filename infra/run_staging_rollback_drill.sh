#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: infra/run_staging_rollback_drill.sh <env_file> <staging_ssh> <primary_ssh> [remote_dir] [backup_dir] [staging_url]"
  echo "Example: infra/run_staging_rollback_drill.sh .env.production.local root@167.172.60.38 root@206.189.116.155"
  exit 2
fi

ENV_FILE="$1"
STAGING_SSH="$2"
PRIMARY_SSH="$3"
REMOTE_DIR="${4:-/opt/buyeros}"
BACKUP_DIR="${5:-/opt/buyeros-backups}"
STAGING_URL="${6:-http://167.172.60.38:8000}"

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

echo "== backup staging =="
BUYEROS_OPS_SUMMARY_DIR="$SUMMARY_DIR" bash "$SCRIPT_DIR/backup_vps.sh" "$STAGING_SSH" "$REMOTE_DIR" "$BACKUP_DIR"

BACKUP_ARCHIVE="$("$PYTHON_BIN" - "$SUMMARY_DIR/backup-latest.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
archive_path = data.get("archive_path") or ""
if ":" not in archive_path:
    raise SystemExit(f"Cannot parse archive_path: {archive_path}")
print(archive_path.split(":", 1)[1])
PY
)"

echo "== rollback staging from latest backup =="
BUYEROS_OPS_SUMMARY_DIR="$SUMMARY_DIR" bash "$SCRIPT_DIR/rollback_vps.sh" "$STAGING_SSH" "$BACKUP_ARCHIVE" "$REMOTE_DIR"

echo "== staging smoke after rollback =="
bash "$SCRIPT_DIR/smoke_api.sh" "$STAGING_URL" "$BUYEROS_API_KEY"

echo "== sync rollback summaries to primary current release =="
ssh "$PRIMARY_SSH" "mkdir -p '$REMOTE_DIR/current/infra/ops_runs'"
rsync -az "$SUMMARY_DIR/" "$PRIMARY_SSH:$REMOTE_DIR/current/infra/ops_runs/"

echo "== verify production ops status =="
curl -fsS -H "Authorization: Bearer ${BUYEROS_API_KEY}" "${PUBLIC_BASE_URL%/}/ops/status" | "$PYTHON_BIN" -m json.tool

echo "Staging rollback drill OK: rollback summary synced to ${PRIMARY_SSH}:${REMOTE_DIR}/current/infra/ops_runs"
