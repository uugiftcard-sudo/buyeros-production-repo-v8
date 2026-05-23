# BuyerOS Next Steps Go-Live Plan

## Current Verified State

- PR branch `cursor/test-additions` is green on GitHub Actions:
  - `lint`
  - `typecheck`
  - `test`
  - `frontend`
  - `docker-build`
- Primary VPS is deployed from clean commit `c25767a`.
- Primary audit passed:
  - env
  - docker compose config
  - HTTPS ping
  - context / dispatcher / run_all smoke
  - three workspace smoke: `buyeros`, `cloth`, `xau`
  - Telegram webhook mock smoke
  - Telegram bot token check
  - primary VPS compose
- Staging SSH was intentionally skipped in the latest audit.

## Immediate P0 Sequence

1. Merge PR #1 after confirming the branch still shows all checks passing.
2. Keep primary VPS pinned to the merged commit or redeploy from `main` after merge.
3. Set the real Telegram webhook to the primary HTTPS endpoint:

   ```bash
   cd /Users/rubykan/Downloads/buyeros-production-repo-v8
   bash infra/set_telegram_webhook.sh \
     .env.production.local \
     https://buyeros.206.189.116.155.sslip.io/telegram/webhook
   ```

4. Run go-live audit after webhook setup:

   ```bash
   cd /Users/rubykan/Downloads/buyeros-production-repo-v8
   ./infra/go_live_audit.sh \
     .env.production.local \
     https://buyeros.206.189.116.155.sslip.io \
     root@206.189.116.155
   ```

5. Start or continue 24h hourly smoke monitoring.

## Local Worktree Hygiene

Before the next deploy from the local machine, resolve current uncommitted changes:

- Keep candidate:
  - `backend/app/context/context_hub.py`: broader fallback for historical session payloads.
  - `infra/smoke_full.sh`: better npm path detection.
  - `infra/smoke_one_click.sh`: better npm path detection.
- Review before keeping:
  - `frontend/tests/buyeros-ui.smoke.spec.ts`: test assertions were loosened; keep only if it still verifies the real three-workspace UI.
- Do not keep:
  - any `NEXT_PUBLIC_*API_KEY` fallback in frontend code.
  - generated smoke logs or pid files.
  - generated `frontend/next-env.d.ts` route-path changes.

## P1 Productization Order

1. CLOTH workflow hardening:
   - refund review states
   - OCR posting
   - reconciliation
   - mismatch alerts
   - daily report push

2. BuyerOS AI Team:
   - provider config screen
   - provider fallback quality checks
   - task rerun / retry
   - memory timeline filtering

3. XAU center:
   - campaign status lifecycle
   - conversion metrics
   - Telegram report card
   - simple CSV export

4. Ops and reliability:
   - staging SSH fix
   - backup / restore drill
   - failover smoke
   - one rollback record with RTO/RPO notes

## Acceptance Commands

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
git status --short
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run build
cd ..
./infra/go_live_audit.sh .env.production.local https://buyeros.206.189.116.155.sslip.io root@206.189.116.155
```

## Decision Rule

Do not deploy from a dirty local worktree. Deploy only from:

- a clean commit that has passed CI, or
- a temporary clean worktree checked out at the target commit.
