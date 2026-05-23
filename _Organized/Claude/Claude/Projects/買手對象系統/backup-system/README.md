# 🛡️ BuyerOS Backup System — Implementation Bundle

> Companion implementation 配合 `BuyerOS-Backup-SOP_1.md`
> 將 SOP 由文件變 production system 嘅完整 ready-to-deploy bundle
> Version: 2026-05-16

---

## 📁 檔案地圖

```
backup-system/
├── README.md                          ← 你而家睇緊呢個
├── SECRETS-CHECKLIST.md               ← 開工前 gather secrets
├── SETUP-PROGRESS.md                  ← Step-by-step 1.5 小時 tracker
│
├── .github/workflows/
│   ├── daily-backup.yml               ← 每日 DB pg_dump → R2
│   └── storage-backup.yml             ← 每週 Storage receipts → R2
│
└── scripts/
    ├── daily-snapshot.sh              ← VPS DigitalOcean snapshot
    ├── health-check.sh                ← 自動 check 3 樣嘢 (替代人手)
    └── restore-test.sh                ← Monthly drill 自動化
```

---

## 🎯 同原 SOP 嘅關係

原 `BuyerOS-Backup-SOP_1.md` = **policy** (講要做乜、點解)
呢個 bundle = **implementation** (具體 file + script + step)

| SOP 段落 | 對應檔案 |
|---------|---------|
| Step 1-2: GitHub repo + secrets | `SETUP-PROGRESS.md` Phase 3 + `SECRETS-CHECKLIST.md` |
| Step 3: daily-backup.yml | `.github/workflows/daily-backup.yml` (improved) |
| Step 4: storage-backup.yml | `.github/workflows/storage-backup.yml` (補上 SOP 漏咗嘅 upload) |
| Step 5: VPS snapshot | `scripts/daily-snapshot.sh` (修正 awk bug) |
| Step 6: Bitwarden | `SECRETS-CHECKLIST.md` 嘅 vault structure 部分 |
| Daily Health Check | `scripts/health-check.sh` (新增 — 自動化 SOP 嘅人手 check) |
| Monthly Test Drill | `scripts/restore-test.sh` (新增 — 自動化 SOP 嘅 manual drill) |

---

## 🚨 同原 SOP 嘅差異 / 修正

| Issue | 原 SOP | 改善 |
|-------|--------|------|
| Storage backup 唔完整 | YAML 得 download，冇 upload | 補上完整 R2 upload + retention |
| Storage hardcode 'documents' bucket | 寫死 | 抽出做 `STORAGE_BUCKET_NAME` secret |
| daily-backup.yml 用 shallwefootball action | 第三方 action 有 supply-chain risk | 改用官方 aws-cli |
| R2 retention 邏輯有 bug | `find -mtime` 用喺 upload **之後** = 無效 | 改成真係去 R2 delete |
| daily-snapshot.sh awk cutoff | `$3 < cutoff` 比較 ISO string 同 epoch，永遠唔會 match | 改用 snapshot name 入面個 date 比較 |
| 缺 `R2_ENDPOINT` secret | secrets table 冇列 | 加入 + 解釋點攞 |
| Daily check 要人手做 | 文字 SOP，靠記性 | 寫埋 `health-check.sh` cron 化 |
| Monthly drill 要人手做 | 文字流程 | 寫埋 `restore-test.sh` 完整自動化 |
| 冇 success notification | 只有 failure alert | 加 ✅ success alert，知個 system 仲生勾勾 |
| 冇 retry logic | 一 fail 就停 | Snapshot 加咗 retry once |
| 冇 backup file size sanity check | Empty dump 都會「成功」 | 加 < 10KB 就 fail |

---

## 🚀 點開始

1. 開 `SECRETS-CHECKLIST.md` → gather 晒 secrets
2. 開 `SETUP-PROGRESS.md` → 由 Phase 0 開始 tick
3. 預計時間: ~1.5 小時 (一氣呵成做最好)
4. 完成後第二日朝早 check Telegram 有冇 ✅ message

---

## 🆘 Stuck 嘅時候

| 症狀 | 通常原因 |
|-----|---------|
| GitHub Actions fail at pg_dump | `SUPABASE_DB_PASSWORD` 唔啱，或者 IP 未 whitelist。Supabase Free / Pro 默認 allow all，但有 firewall 要加 GitHub Actions IP range |
| R2 upload 403 | Token permission 唔啱，要 Object Read & Write，要 scope 啱 bucket |
| R2 endpoint 404 / no such host | Endpoint URL 無 `https://`，或者寫錯 account ID |
| Telegram 收唔到 alert | `ADMIN_TG_ID` 唔啱（要去 @userinfobot 攞），或者 bot 未被你 /start 過 |
| doctl auth fail | API token 要係 read+write scope |
| Restore drill fail at psql | `TEST_DB_PASSWORD` 唔啱，或者 test project IP whitelist |

如果 stuck → screenshot 個 error，問返我或工程師朋友。

---

## 🔄 維護週期

| 頻率 | 做乜 |
|------|------|
| 每日 (auto) | DB backup + VPS snapshot + health check |
| 每週 (auto) | Storage backup |
| 每月 (semi-auto) | Restore drill (跑 `restore-test.sh`) |
| 每 3 個月 | Review 呢份 README + 原 SOP，update outdated 嘅嘢 |
| 每 6 個月 | Rotate 晒所有 secrets (參考 `SECRETS-CHECKLIST.md` 個 rotation table) |

---

## ⚠️ 一啲我冇做但你應該諗嘅嘢

呢個 bundle cover 咗 backup，但 **disaster recovery (DR)** 仲有空間：

- **Region failure**: 而家 VPS 喺 DigitalOcean 一個 region，R2 多 region 但 Supabase 一個 region。如果 AWS/GCP 大爆 region，要諗多區 fail-over
- **Restore time**: 你而家最快 10-30 分鐘可以搞返 DB，但客戶 / Telegram bot 嗰邊體驗會點？需要 status page / customer comms playbook
- **Compliance**: 你話完整會計（發票 + 稅 + 月結），即係可能要證明 backup 嘅 immutability。R2 + GitHub Actions 而家可以 delete backup → 唔係 audit-grade。要再升級可以開 R2 object lock / WORM
- **Secret detection**: 你應該裝 GitHub secret scanning + pre-commit hook (`gitleaks`)，避免有人意外 commit secrets

呢啲唔影響呢個 bundle 嘅 setup，做完先諗都得。

---

## 📚 Reference

- 原 SOP: `../BuyerOS-Backup-SOP_1.md`
- Supabase pg_dump docs: https://supabase.com/docs/guides/platform/migrating-and-upgrading-projects
- Cloudflare R2 S3 API: https://developers.cloudflare.com/r2/api/s3/api/
- doctl reference: https://docs.digitalocean.com/reference/doctl/
