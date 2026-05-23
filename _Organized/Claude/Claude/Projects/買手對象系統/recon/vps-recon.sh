#!/bin/bash
#
# BuyerOS VPS Reconnaissance
# 用途: 一次過掃 VPS 揾出 app code 喺邊、邊個 service 跑緊、邊啲 cron set 咗
#
# 點用:
#   1. ssh root@206.189.116.155
#   2. cat > /tmp/vps-recon.sh   ← paste 呢個 script 內容
#      <paste, Ctrl-D>
#   3. chmod +x /tmp/vps-recon.sh
#   4. /tmp/vps-recon.sh 2>&1 | tee /tmp/vps-recon-report.txt
#   5. cat /tmp/vps-recon-report.txt  ← copy 全部貼返畀我
#
# 唔會改任何嘢，純 read-only。

set +e
HR="=========================================="
section() { echo ""; echo "$HR"; echo "## $1"; echo "$HR"; }

section "0. Identity & Time"
date
hostname
echo "Public IP: $(curl -s ifconfig.me || echo unknown)"
echo "Uptime: $(uptime)"

section "1. OS Info"
cat /etc/os-release 2>/dev/null | head -10
echo ""
echo "Kernel: $(uname -r)"
echo "Arch:   $(uname -m)"

section "2. Disk usage"
df -h / 2>/dev/null
echo ""
echo "Top 10 大 folder under / (>100MB):"
du -h --max-depth=2 / 2>/dev/null | awk '$1 ~ /[0-9]+G/ || $1 ~ /[0-9]{3,}M/' | sort -hr | head -10

section "3. Memory & CPU"
free -h
echo ""
echo "CPU model:"
grep "model name" /proc/cpuinfo | head -1
echo "CPU cores: $(nproc)"

section "4. Languages / Runtimes installed"
for cmd in python python3 node deno bun ruby go java php docker docker-compose nginx caddy pm2 systemctl supervisorctl; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "✓ $cmd: $($cmd --version 2>&1 | head -1)"
  fi
done

section "5. Running systemd services (active only)"
systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | awk '{print $1, $4}' | head -30

section "6. Top 20 processes (by mem)"
ps aux --sort=-%mem 2>/dev/null | head -21

section "7. Listening ports + owning process"
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null

section "8. Active crontabs"
echo "--- root crontab ---"
crontab -l 2>/dev/null || echo "(none)"
echo ""
echo "--- /etc/crontab + /etc/cron.d ---"
cat /etc/crontab 2>/dev/null
ls -la /etc/cron.*/ 2>/dev/null

section "9. Docker (if any)"
if command -v docker >/dev/null 2>&1; then
  echo "--- docker ps -a ---"
  docker ps -a 2>/dev/null
  echo ""
  echo "--- docker images ---"
  docker images 2>/dev/null
  echo ""
  echo "--- docker-compose files ---"
  find / -name "docker-compose*.yml" -not -path "*/snap/*" 2>/dev/null | head -20
else
  echo "Docker not installed"
fi

section "10. 揾 application code (heuristic)"
echo "--- 揾 entry point file ---"
find /root /home /opt /srv /var/www -maxdepth 5 -type f \( \
  -name "main.py" -o -name "app.py" -o -name "bot.py" -o \
  -name "server.js" -o -name "index.js" -o -name "index.ts" -o \
  -name "app.ts" -o -name "main.ts" -o -name "mod.ts" -o \
  -name "package.json" -o -name "pyproject.toml" -o \
  -name "deno.json" -o -name "deno.jsonc" -o \
  -name "Dockerfile" -o -name "Procfile" \
  \) 2>/dev/null | head -40
echo ""
echo "--- 揾 .env / config file (數量，唔 print 內容) ---"
find /root /home /opt /srv -maxdepth 5 \( -name ".env" -o -name ".env.*" -o -name "*.env" \) 2>/dev/null | head -20
echo ""
echo "--- 揾 git repo ---"
find /root /home /opt /srv -maxdepth 4 -type d -name ".git" 2>/dev/null | head -10

section "11. Backup README 提到嘅 /root/ai-os/"
if [ -d /root/ai-os ]; then
  echo "✓ /root/ai-os EXISTS"
  ls -la /root/ai-os 2>/dev/null
  echo ""
  echo "--- /root/ai-os 入面有乜 ---"
  find /root/ai-os -maxdepth 3 -type f 2>/dev/null | head -40
  echo ""
  echo "--- 入面 git log (如有) ---"
  if [ -d /root/ai-os/.git ]; then
    git -C /root/ai-os log --oneline -20 2>/dev/null
    echo ""
    git -C /root/ai-os remote -v 2>/dev/null
  else
    echo "(無 .git folder)"
  fi
else
  echo "✗ /root/ai-os 唔存在 — backup README 講錯，或者 code 喺其他位"
fi

section "12. Nginx / Caddy / reverse proxy config"
if [ -d /etc/nginx ]; then
  echo "--- Nginx sites ---"
  ls /etc/nginx/sites-enabled/ 2>/dev/null
  echo ""
  for f in /etc/nginx/sites-enabled/*; do
    [ -f "$f" ] && echo "=== $f ===" && grep -E "server_name|proxy_pass|root|listen" "$f" 2>/dev/null
  done
fi
if [ -f /etc/caddy/Caddyfile ]; then
  echo "--- Caddyfile ---"
  cat /etc/caddy/Caddyfile
fi

section "13. doctl auth status"
if command -v doctl >/dev/null 2>&1; then
  doctl auth list 2>/dev/null
else
  echo "doctl not installed yet (backup SOP requires this)"
fi

section "14. supabase CLI status"
if command -v supabase >/dev/null 2>&1; then
  echo "Supabase CLI: $(supabase --version 2>/dev/null)"
  echo "Linked project (if logged in):"
  supabase projects list 2>/dev/null | head -10
else
  echo "Supabase CLI 唔喺 VPS — 一般本機用，唔係問題"
fi

section "15. 環境 secrets (count only, NEVER print)"
echo "/.env count: $(find /root /home /opt /srv -maxdepth 5 \( -name ".env" -o -name ".env.*" \) 2>/dev/null | wc -l)"
echo "(內容唔會 print，避免洩漏 secret)"

echo ""
echo "$HR"
echo "## DONE — copy 全部 output 貼返畀 Claude"
echo "$HR"
