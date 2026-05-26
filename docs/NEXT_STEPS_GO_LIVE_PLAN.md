# BuyerOS Fast-Push Next Steps

This file is the current operating plan for BuyerOS go-live follow-up. Keep it
short, executable, and collision-safe.

## Current Verified State

- Current branch baseline: `main` at `0f0df9e`.
- Primary production:
  - Host: `206.189.116.155`
  - URL: `https://buyeros.206.189.116.155.sslip.io`
  - Role: production API, UI, Redis, Telegram webhook, provider routing.
- Staging / hot standby:
  - Host: `167.172.60.38`
  - URL: `https://buyeros.167.172.60.38.sslip.io`
  - Role: staging, failover smoke, rollback drills, ops checks.
- Latest verified audit passed:
  - env
  - docker compose config
  - HTTPS ping
  - context / dispatcher / run_all smoke
  - three canonical line smoke: `buyer_ai`, `commerce`, `xau`
  - Telegram webhook mock smoke
  - Telegram bot token check
  - primary compose
  - staging SSH
- Real Telegram webhook target stays on primary only.
- 24h smoke heartbeat is active and should stay quiet unless a gate fails.

## Fast-Push Rules

- Every plan uses only three groups: `today`, `next`, `defer`.
- Do not restate history unless a status changed.
- Do not expand UI unless backend behavior is already wired and tested.
- Do not deploy from a dirty worktree.
- Do not work directly on shared `main` for new feature changes.
- Use a dedicated branch or worktree for new work:

  ```bash
  git switch -c codex/<short-task-name>
  ```

- If another conversation leaves dirty changes, stop and audit instead of
  overwriting them.

## Today

1. Complete 24h smoke monitoring.
   - Leave heartbeat active.
   - Notify only on failing gate.
   - After 24 hours, summarize pass/fail and pause the heartbeat.

2. Do one real Telegram user test.
   - Send `退款 991`.
   - Send `991 點？`.
   - Expected: second message recalls persisted refund state.

3. Stabilize provider status.
   - Check Claude/Cursor OpenRouter model slugs.
   - Keep OpenAI fallback active.
   - `/providers` must show ready/degraded/not_configured clearly.

## Next

1. Commerce first real business flow.
   - Shop order / inventory / support / shop finance path.
   - Daily shop report push.
   - Keep buyer refund reconciliation and OCR posting under `buyer_ai`.

2. Buyer AI refund/reconciliation flow.
   - Refund review states.
   - OCR posting.
   - Manual review queue.

3. Reliability drill.
   - Run staging rollback drill from latest staging backup.
   - Run failover smoke from primary to staging.
   - Record RTO/RPO result in docs.

4. BuyerOS AI Team ops.
   - Provider fallback quality checks.
   - Task rerun / retry.
   - Memory timeline filtering only if backend data is already present.

## Defer

- Extra dashboard panels.
- Full OCR reconciliation productization.
- XAU advanced campaign lifecycle.
- Multi-provider direct credentials beyond OpenRouter unless needed for cost or
  reliability.

## Acceptance Commands

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8

git status --short
git branch --show-current
git log --oneline -3

./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run build
cd ..

bash infra/go_live_audit.sh \
  .env.production.local \
  https://buyeros.206.189.116.155.sslip.io \
  root@206.189.116.155 \
  root@167.172.60.38
```

## Collision Checks

```bash
git worktree list
ls /Users/rubykan/.codex/automations
ssh root@206.189.116.155 'test ! -f /tmp/buyeros-deploy.lock && echo no-deploy-lock'
```

## Decision Rule

Production accepts clean commits only. Staging may preview new branches, but the
commit hash must be known and written in the handoff.
