#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: infra/audit_vps.sh <ssh_target>"
  echo "Example: infra/audit_vps.sh root@206.189.116.155"
  exit 1
fi

SSH_TARGET="$1"

ssh "$SSH_TARGET" 'bash -s' <<'REMOTE'
set -euo pipefail
echo "=== Host ==="
hostnamectl | sed -n '1,8p' || true
echo
echo "=== Disk ==="
df -h
echo
echo "=== Top directories under / (size) ==="
du -xh --max-depth=1 / 2>/dev/null | sort -h | tail -n 15
echo
echo "=== Top directories under /var (size) ==="
du -xh --max-depth=1 /var 2>/dev/null | sort -h | tail -n 15
echo
if command -v docker >/dev/null 2>&1; then
  echo "=== Docker system df ==="
  docker system df || true
  echo
  echo "=== Docker containers ==="
  docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Size}}"
  echo
  echo "=== Docker volumes ==="
  docker volume ls
else
  echo "Docker not installed."
fi
echo
echo "=== Journal disk usage ==="
journalctl --disk-usage || true
echo
echo "=== Large files (>500MB) ==="
find / -xdev -type f -size +500M 2>/dev/null | head -n 50
REMOTE

