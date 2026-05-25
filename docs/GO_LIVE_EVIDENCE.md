# BuyerOS / XAU / CLOTH Go-Live Evidence

Last updated: 2026-05-25

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
cd /Users/rubykan/Downloads/buyeros-production-repo-v8/backend
/Users/rubykan/miniconda3/bin/python -m pytest tests/ -v --tb=short
# 225 passed, 100 warnings
```

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend
/usr/local/bin/npm run lint
/usr/local/bin/npm run build
# lint/typecheck passed; Next.js production build passed
```

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/usr/local/bin/npx --yes supabase secrets list --project-ref jnzdklfjdjmhjrhntljp
# Required secret names verified: OPENAI_API_KEY, ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, HEYGEN_API_KEY
```

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

Latest result:

```text
Go-live audit OK.
```

Verified gates:

- env validation
- HTTPS ping
- four systems smoke
- Telegram webhook mock smoke
- Telegram bot token
- primary VPS compose
- staging SSH

## Phase 6 DB restore smoke

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
SUPABASE_URL="$(grep '^SUPABASE_URL=' .env.production | cut -d= -f2-)" \
SUPABASE_SERVICE_ROLE_KEY="$(grep '^SUPABASE_SERVICE_ROLE_KEY=' .env.production | cut -d= -f2-)" \
bash infra/restore_test.sh
```

Latest result:

```text
agent_memory rows: 8819
Insert OK
Read back OK
Test row cleaned up
RESULT: PASS - DB restore smoke passed
```

## Rollback

Use the existing VPS rollback script against the target host and the last verified backup archive.

```bash
bash infra/rollback_vps.sh root@206.189.116.155
```

## Remaining risks

- CLOTH v1 finance/inventory/support APIs currently use in-memory seed data; production needs persistent storage before real operations.
- XAU real-time news requires `NEWS_API_URL` and optional `NEWS_API_KEY`; without them it returns a safe fallback alert instead of fake news.
- AI virtual host features must be disclosed as AI presenter; do not create fake viewers, fake comments, or undisclosed human impersonation.
