#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: infra/cleanup_vps.sh <ssh_target> [--execute] [--keep-path /opt/buyeros]"
  echo "Examples:"
  echo "  infra/cleanup_vps.sh root@206.189.116.155"
  echo "  infra/cleanup_vps.sh root@206.189.116.155 --execute --keep-path /opt/buyeros"
  exit 1
fi

SSH_TARGET="$1"
shift

MODE="dry-run"
KEEP_PATHS=("/opt/buyeros")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      MODE="execute"
      shift
      ;;
    --keep-path)
      KEEP_PATHS+=("$2")
      shift 2
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

KEEP_JOINED=""
for p in "${KEEP_PATHS[@]}"; do
  KEEP_JOINED+="$p"$'\n'
done

ssh "$SSH_TARGET" "MODE='$MODE' bash -s" <<REMOTE
set -euo pipefail
MODE="\${MODE:-dry-run}"
KEEP_PATHS=\$(cat <<'EOF'
$KEEP_JOINED
EOF
)

echo "Cleanup mode: \$MODE"
echo "Protected paths:"
printf '%s\n' "\$KEEP_PATHS" | sed '/^$/d'

run_cmd() {
  if [[ "\$MODE" == "execute" ]]; then
    echo "[EXEC] \$*"
    eval "\$*"
  else
    echo "[DRY ] \$*"
  fi
}

echo
echo "=== Before cleanup disk usage ==="
df -h

echo
echo "=== apt cache cleanup ==="
run_cmd "apt-get clean"
run_cmd "rm -rf /var/cache/apt/archives/*.deb /var/lib/apt/lists/*"

echo
echo "=== temp folders cleanup ==="
run_cmd "find /tmp -mindepth 1 -maxdepth 1 -mtime +2 -exec rm -rf {} +"
run_cmd "find /var/tmp -mindepth 1 -maxdepth 1 -mtime +2 -exec rm -rf {} +"

echo
echo "=== journal cleanup ==="
run_cmd "journalctl --vacuum-time=7d"
run_cmd "journalctl --vacuum-size=200M"

if command -v docker >/dev/null 2>&1; then
  echo
  echo "=== docker cleanup ==="
  run_cmd "docker container prune -f"
  run_cmd "docker image prune -af"
  run_cmd "docker builder prune -af"
  run_cmd "docker volume prune -f"
fi

echo
echo "=== candidate old dirs in /opt (not deleted automatically) ==="
find /opt -mindepth 1 -maxdepth 1 -type d 2>/dev/null | while read -r d; do
  if printf '%s\n' "\$KEEP_PATHS" | grep -qx "\$d"; then
    echo "[KEEP] \$d"
  else
    du -sh "\$d" 2>/dev/null || true
  fi
done

echo
echo "=== After cleanup disk usage ==="
df -h
REMOTE

