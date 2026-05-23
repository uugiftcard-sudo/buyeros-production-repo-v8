# 🚀 Setup Progress Tracker

> 由 0 到 production，預計 ~1.5 小時
> 跟住做，每完成一 step tick 一格

---

## Phase 0: 準備 (15 分鐘)

- [ ] 開咗 Bitwarden free account
- [ ] 開好 `BuyerOS Vault` folder (參考 `SECRETS-CHECKLIST.md` 嘅 structure)
- [ ] Gather 晒以下 secrets 入 Bitwarden：
  - [ ] Supabase: project ref, DB password, service_role key
  - [ ] Cloudflare: account ID, R2 endpoint, R2 access/secret key
  - [ ] DigitalOcean: API token
  - [ ] Telegram: bot token, admin user ID

---

## Phase 1: Cloudflare R2 (10 分鐘)

- [ ] Cloudflare → R2 → Create bucket: `buyeros-backups`
- [ ] R2 → Manage R2 API Tokens → Create API Token
  - Permission: **Object Read & Write**
  - Bucket: 限定 `buyeros-backups`
  - Copy Access Key + Secret Key 入 Bitwarden
- [ ] R2 → 揀 bucket → Settings → Copy S3 API endpoint
  (格式: `https://<accountid>.r2.cloudflarestorage.com`)

---

## Phase 2: Test Supabase Project (10 分鐘) — 為 monthly drill 準備

- [ ] Supabase → New Project: `buyeros-restore-test`
  - Region 揀同 prod 一樣
  - Plan: Free tier 夠（drill 完 truncate）
- [ ] Project Settings → Database → 抄低 Connection String 嘅 password
- [ ] 入 Bitwarden: `Supabase / Test Project Ref + Password`

---

## Phase 3: GitHub Repo + Workflows (20 分鐘)

- [ ] GitHub → New Repository: `buyeros-backups`
  - Private
  - Initialize with README
- [ ] Clone 落 local:
  ```
  git clone git@github.com:<你>/buyeros-backups.git
  cd buyeros-backups
  ```
- [ ] Copy 兩個 workflow file 過去:
  ```
  mkdir -p .github/workflows
  cp ../買手對象系統/backup-system/.github/workflows/*.yml .github/workflows/
  ```
- [ ] GitHub Repo → Settings → Secrets and variables → Actions
- [ ] 加晒 10 個 secrets（睇 `SECRETS-CHECKLIST.md` 嗰個 table）
- [ ] Commit + push:
  ```
  git add .github/workflows
  git commit -m "Add daily DB + weekly storage backup workflows"
  git push
  ```
- [ ] GitHub → Actions tab → 揀 `Daily Supabase DB Backup` → Run workflow（手動 trigger）
- [ ] 等 1-3 分鐘，確認：
  - [ ] Workflow run 變綠 ✅
  - [ ] R2 bucket 入面有 `supabase-db/buyeros-YYYY-MM-DD.sql.gz`
  - [ ] Telegram 收到「✅ BuyerOS DB backup OK」message
- [ ] 同樣手動 trigger `Weekly Supabase Storage Backup` 試一次

⚠️ **如果 fail**：睇 Actions log 邊一 step 出事 → 大部分情況係 secrets 名 typo 或 R2_ENDPOINT 漏咗 https://

---

## Phase 4: VPS Snapshot (20 分鐘)

- [ ] DigitalOcean → 揀你個 droplet (206.189.116.155) → Backups
- [ ] **首選**: Enable Backups (USD$1.20/月) — 直接搞掂，跳到 Phase 5
- [ ] **如果想 free**: 跟以下 setup doctl daily snapshot:
  ```
  ssh root@206.189.116.155
  
  # Install doctl
  cd /tmp
  wget https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz
  tar xf doctl-1.104.0-linux-amd64.tar.gz
  mv doctl /usr/local/bin
  
  # Auth
  doctl auth init  # 入 DO API token
  
  # 部署 script
  ```
- [ ] Copy `daily-snapshot.sh` 上 VPS:
  ```
  scp scripts/daily-snapshot.sh root@206.189.116.155:/root/
  ```
- [ ] 喺 VPS:
  ```
  chmod +x /root/daily-snapshot.sh
  
  # 寫 secrets
  cat > /root/.snapshot.env <<EOF
  export TG_TOKEN="your_bot_token"
  export TG_ADMIN="your_user_id"
  EOF
  chmod 600 /root/.snapshot.env
  
  # 試跑一次
  /root/daily-snapshot.sh
  ```
- [ ] 確認：
  - [ ] DigitalOcean → Snapshots 出現 `buyeros-YYYY-MM-DD`
  - [ ] Telegram 收到「✅ Snapshot done」message
- [ ] 加 crontab:
  ```
  (crontab -l 2>/dev/null ; echo "0 2 * * * /root/daily-snapshot.sh >> /var/log/buyeros-snapshot.log 2>&1") | crontab -
  ```

---

## Phase 5: Health Check (15 分鐘)

- [ ] 喺 GitHub 開 fine-grained PAT:
  - Settings → Developer settings → Personal access tokens → Fine-grained tokens
  - Repository: only `buyeros-backups`
  - Permissions: Actions = Read
  - Copy token 入 Bitwarden
- [ ] Copy `health-check.sh` 上 VPS:
  ```
  scp scripts/health-check.sh root@206.189.116.155:/root/
  ```
- [ ] 喺 VPS:
  ```
  chmod +x /root/health-check.sh
  
  cat > /root/.health-check.env <<EOF
  export GITHUB_TOKEN="ghp_xxx..."
  export GITHUB_REPO="<你>/buyeros-backups"
  export R2_ACCESS_KEY="..."
  export R2_SECRET_KEY="..."
  export R2_BUCKET="buyeros-backups"
  export R2_ENDPOINT="https://<id>.r2.cloudflarestorage.com"
  export TG_TOKEN="..."
  export TG_ADMIN="..."
  EOF
  chmod 600 /root/.health-check.env
  
  # 安裝 awscli (R2 用)
  apt-get install -y awscli
  
  # 試跑（如果 backup workflow 已經跑過，呢度應該見 ALL OK）
  /root/health-check.sh
  ```
- [ ] 加 crontab (每朝 9 點 check):
  ```
  (crontab -l 2>/dev/null ; echo "0 9 * * * /root/health-check.sh >> /var/log/buyeros-health.log 2>&1") | crontab -
  ```

---

## Phase 6: Restore Drill (20 分鐘 — 第一次 setup)

- [ ] 喺你 local machine（macOS）:
  ```
  brew install postgresql awscli
  ```
- [ ] Copy `restore-test.sh` 落本機:
  ```
  cp scripts/restore-test.sh ~/buyeros-restore-test.sh
  chmod +x ~/buyeros-restore-test.sh
  ```
- [ ] 改 script 入面個 `CRITICAL_TABLES` 陣列，改成你實際嘅核心 table 名（buyers / transactions / refunds 同 actual table 名要一致）
- [ ] 寫 secrets:
  ```
  cat > ~/.buyeros-restore.env <<EOF
  export PROD_PROJECT_REF="jnzdklfjdjmhjrhntljp"
  export TEST_PROJECT_REF="<test project ref>"
  export TEST_DB_PASSWORD="..."
  export R2_ACCESS_KEY="..."
  export R2_SECRET_KEY="..."
  export R2_BUCKET="buyeros-backups"
  export R2_ENDPOINT="https://<id>.r2.cloudflarestorage.com"
  export TG_TOKEN="..."
  export TG_ADMIN="..."
  EOF
  chmod 600 ~/.buyeros-restore.env
  ```
- [ ] 跑一次 drill:
  ```
  ~/buyeros-restore-test.sh
  ```
- [ ] 確認：
  - [ ] Test project 入面 tables 數 ≥ 20
  - [ ] Telegram 收到「✅ Restore drill PASSED」
- [ ] 用 macOS Calendar 或 Google Calendar set monthly reminder：每月 1 號 9am

---

## ✅ Done Checklist

當你 tick 完晒上面，再做最後驗證：

- [ ] **第二日朝早**: Telegram 自動收到「✅ BuyerOS DB backup OK」(由 cron 跑出嚟)
- [ ] **第二日朝早**: Telegram 自動收到「✅ Snapshot done」
- [ ] **第二日 9am**: Health check 跑完，冇 alert（即係 3/3 ok）
- [ ] **下個禮拜一**: 收到 Storage backup 成功 alert
- [ ] **下個月 1 號**: 自己手動跑 restore drill

---

## 💸 月費 estimate

| Item | 月費 |
|------|------|
| Cloudflare R2 | $0 (10GB free tier) |
| GitHub Actions | $0 (2000 min free tier，daily backup ~5min/run) |
| DigitalOcean Backups | $1.20 (or $0 if doctl path) |
| Bitwarden | $0 |
| Test Supabase Project | $0 (free tier) |
| **Total** | **~$1.20 USD / 月** |

對比生意斷一日 = HK$500K：**ROI 系數無限大**。
