# BuyerOS / XAU / CLOTH Go-Live Evidence

Last updated: 2026-05-24

## Release posture

Production must only be deployed from a clean commit after CI and smoke pass.
Do not deploy directly from a dirty local worktree.

## Current three-line contract

| Line | Canonical ID | Scope |
| --- | --- | --- |
| 買手 AI 中樞 | `buyer_ai` | BuyerOS / AI Team / 買手 Report / 退款 / OCR 入帳 / 對帳 / 採購 ROI |
| 網店自動系統 | `commerce` | AI 虛擬主播帶貨 / 訂單 / 庫存 / 客服 / 網店收支報表 |
| XAU 系統 | `xau` | AI 直播 / 虛擬主播 / 實時新聞提示 / promo / conversion / metrics |

## Latest local verification

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
./.venv/bin/python -m pytest -q backend/tests/test_p0_command_center.py backend/tests/test_three_line_modules.py
# 21 passed
```

```bash
cd /Users/rubykan/Documents/XAU
npm run test:server
# 18 passed
```

```bash
cd /Users/rubykan/Documents/CLOTH
npm run build
# api tsc passed; web tsc && vite build passed
```

## Production gate

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
./infra/go_live_audit.sh .env.production.local https://buyeros.206.189.116.155.sslip.io root@206.189.116.155 root@167.172.60.38
```

Required result before client handoff:

```text
Go-live audit OK.
```

Known current blocker if this fails:

- Production may still be running an older canonical project set (`buyeros / cloth / xau`) while local code expects `buyer_ai / commerce / xau`.

## Rollback

Use the existing VPS rollback script against the target host and the last verified backup archive.

```bash
bash infra/rollback_vps.sh root@206.189.116.155
```

## Remaining risks

- CLOTH v1 finance/inventory/support APIs currently use in-memory seed data; production needs persistent storage before real operations.
- XAU real-time news requires `NEWS_API_URL` and optional `NEWS_API_KEY`; without them it returns a safe fallback alert instead of fake news.
- AI virtual host features must be disclosed as AI presenter; do not create fake viewers, fake comments, or undisclosed human impersonation.
