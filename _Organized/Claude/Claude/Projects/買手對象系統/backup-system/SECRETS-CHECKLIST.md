# 🔐 Secrets Checklist

> 開工前先 gather 晒所有 secrets，唔好 setup 到一半先發現缺 key。
> 補上原 SOP 缺嘅 `R2_ENDPOINT`、`STORAGE_BUCKET_NAME` 等。

---

## 📍 Secrets 放邊度

| 用途 | 放邊度 |
|------|-------|
| GitHub Actions 用嘅 (DB / Storage backup) | **GitHub Repo → Settings → Secrets** |
| VPS daily-snapshot.sh 用嘅 | `/root/.snapshot.env` (chmod 600) |
| Local restore-test.sh 用嘅 | `~/.buyeros-restore.env` (chmod 600) |
| Health-check.sh 用嘅 | `/root/.health-check.env` (chmod 600) |
| 永久 vault (master copy) | **Bitwarden / 1Password** — folder `BuyerOS Vault` |

⚠️ **永遠唔好** put secrets 入: email, Telegram chat, Google Doc, Notion plain text, git commit。

---

## ✅ GitHub Repo Secrets (給 daily-backup.yml + storage-backup.yml)

去 `Settings → Secrets and variables → Actions → New repository secret`，逐個加：

| Secret Name | 攞處 | 範例值 |
|-------------|------|--------|
| `SUPABASE_DB_PASSWORD` | Supabase Dashboard → Project Settings → Database → Connection String → 入面個 password | `xxx...` |
| `SUPABASE_PROJECT_REF` | 你個 project ref | `jnzdklfjdjmhjrhntljp` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Project Settings → API → service_role (secret) | `eyJhbGc...` |
| `STORAGE_BUCKET_NAME` | 你個 storage bucket 名 (原 SOP hardcode 'documents'，呢度抽出嚟) | `documents` |
| `R2_ACCESS_KEY` | Cloudflare Dashboard → R2 → Manage R2 API Tokens → Create API Token | `xxx...` |
| `R2_SECRET_KEY` | 同上，create token 嗰陣會 show 一次，要即刻 copy | `xxx...` |
| `R2_BUCKET` | 你開個 R2 bucket 名 | `buyeros-backups` |
| `R2_ENDPOINT` | **原 SOP 漏咗呢個** — Cloudflare R2 → 揀 bucket → Settings → S3 API endpoint | `https://<accountid>.r2.cloudflarestorage.com` |
| `TELEGRAM_BOT_TOKEN` | BotFather → 你個 bot token (建議用 sub-bot 專做 alerts，唔好用 prod bot) | `1234567890:xxx...` |
| `ADMIN_TG_ID` | 你個 Telegram user ID (向 @userinfobot 發 /start 攞) | `123456789` |

---

## ✅ VPS `/root/.snapshot.env` (給 daily-snapshot.sh)

```bash
# 喺 VPS run:
sudo nano /root/.snapshot.env
sudo chmod 600 /root/.snapshot.env
```

內容：

```
export TG_TOKEN="同上 TELEGRAM_BOT_TOKEN"
export TG_ADMIN="同上 ADMIN_TG_ID"
```

⚠️ doctl auth 唔放 env，係 `doctl auth init` 嗰陣存喺 `~/.config/doctl/config.yaml`，記住一次過 setup。

---

## ✅ Local `~/.buyeros-restore.env` (給 restore-test.sh)

```bash
nano ~/.buyeros-restore.env
chmod 600 ~/.buyeros-restore.env
```

內容：

```
export PROD_PROJECT_REF="jnzdklfjdjmhjrhntljp"
export TEST_PROJECT_REF="<新開個 test project ref>"
export TEST_DB_PASSWORD="<test project DB password>"
export R2_ACCESS_KEY="..."
export R2_SECRET_KEY="..."
export R2_BUCKET="buyeros-backups"
export R2_ENDPOINT="https://<accountid>.r2.cloudflarestorage.com"
export TG_TOKEN="..."
export TG_ADMIN="..."
```

⚠️ **必須開一個獨立 test Supabase project** — 唔好用 prod project 做 restore drill，會 DROP 晒 tables。

---

## ✅ VPS `/root/.health-check.env` (給 health-check.sh)

```bash
sudo nano /root/.health-check.env
sudo chmod 600 /root/.health-check.env
```

內容：

```
export GITHUB_TOKEN="<PAT with actions:read scope>"
export GITHUB_REPO="<你 username>/buyeros-backups"
export R2_ACCESS_KEY="..."
export R2_SECRET_KEY="..."
export R2_BUCKET="buyeros-backups"
export R2_ENDPOINT="https://<accountid>.r2.cloudflarestorage.com"
export TG_TOKEN="..."
export TG_ADMIN="..."
```

GitHub PAT 攞處：GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens →
- Repository access: only `buyeros-backups`
- Permissions: Actions = Read

---

## 🗄️ Bitwarden Master Vault Structure

```
BuyerOS Vault/
├── Supabase
│   ├── Project Ref (item)
│   ├── DB Password (item)
│   ├── Service Role Key (item)
│   └── Anon Key (item, just in case)
├── Cloudflare R2
│   ├── Account ID (item)
│   ├── R2 Endpoint URL (item)
│   ├── API Token: Backups (Access Key + Secret Key)
│   └── Bucket Name (item)
├── DigitalOcean
│   ├── API Token (item)
│   ├── Droplet IP: 206.189.116.155 (item)
│   └── SSH Root Password / Key (item)
├── Telegram
│   ├── Bot Token: Prod (item)
│   ├── Bot Token: Alerts (item, 建議分開)
│   └── Admin User ID (item)
└── GitHub
    ├── PAT: actions-read (item)
    └── Repo: buyeros-backups URL (item)
```

---

## 🚨 Rotation Schedule

每 6 個月 rotate 一次：

- [ ] Supabase DB password
- [ ] Supabase Service Role Key
- [ ] R2 API Token
- [ ] DigitalOcean API Token
- [ ] GitHub PAT

每**即刻** rotate 嘅情況：

- 有人離職（睇過任何 secret）
- 任何一個 key 出現喺 git / chat / log
- 收到 Cloudflare / Supabase / DO 嘅 unusual activity 通知
