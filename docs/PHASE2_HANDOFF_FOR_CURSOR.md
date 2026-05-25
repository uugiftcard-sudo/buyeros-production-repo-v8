# Phase 2 Handoff For Cursor / Parallel AI

Last verified: 2026-05-25

Purpose: give the parallel AI a current execution map so it does not repeat merged PR work or mix unrelated dirty files.

## Do Not Repeat

These tasks are already done:

1. XAU PR #3 is merged into `main`.
   - Merge commit: `c7851e9`
   - Fresh merged-main server test passed: `18 pass / 0 fail`
2. CLOTH PR #6 is merged.
   - Merge commit: `d4512c1`
   - Base branch: `cursor/github-actions-workflows`
   - Fresh target-branch lint/build passed with 7 warnings and 0 errors.
3. BuyerOS PR #11 is merged.
   - Merge commit: `992cde3`
4. BuyerOS Phase 2 runtime integration contracts are covered in `backend/tests/test_integration_routing.py`.
   - XAU client: `GET /api/news/latest`, `POST /api/ai/script`
   - CLOTH client: `GET /api/live/readiness`, `POST /api/live/selling-plan`
   - Dispatcher: configured `xau` and `commerce` routes complete through their integration clients

## Work Boundaries

### BuyerOS Agent Can Work On

- Three-system integration smoke:
  - BuyerOS calls XAU `/api/news/latest`
  - BuyerOS calls XAU `/api/ai/script`
  - BuyerOS calls CLOTH live/readiness or selling-plan endpoint if present
- Task Dispatcher mapping:
  - `buyer_ai`: report/refund/OCR/reconcile
  - `commerce`: shop finance/order/support/inventory/live selling
  - `xau`: live stream/promo/conversion/metrics/news
- Ops documentation and audit evidence.

Avoid:

- Editing `.env*`
- Printing secrets
- Re-deploying production from a dirty tree

### XAU Agent Can Work On

- OBS panel/overlay stability.
- Live scheduler and script rotator.
- Real-time news display in live room and app.
- Member/lead/quiz system.
- Analytics for real user actions.

Avoid:

- Fake fans, fake viewers, fake comments, fake testimonials, or fake social proof.
- Bulk committing the current dirty tree.
- Re-adding TTS route/service without diffing against `origin/main`.

### CLOTH Agent Can Work On

- Confirm merge path from `cursor/github-actions-workflows` to production `main`.
- Commerce live-selling flow:
  - product data
  - inventory check
  - support status
  - finance/reporting
- Agent skills:
  - sourcing
  - listing
  - fulfillment
  - video script

Avoid:

- Assuming PR #6 is already in production main unless verified.
- Mixing scraper experiments with production dashboard fixes in one PR.

## Immediate Parallel Work Plan

### Track 1: Release Stability

Owner: any agent not editing feature files.

Tasks:

1. Verify BuyerOS production still passes:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests/test_integration_routing.py -v --tb=short
./infra/go_live_audit.sh .env.production.local https://buyeros.206.189.116.155.sslip.io root@206.189.116.155 root@167.172.60.38
```

2. Verify XAU main:

```bash
cd /Users/rubykan/Documents/XAU
git fetch origin main
git switch main
git pull origin main
cd server
npm test
```

3. Verify CLOTH target branch:

```bash
cd /Users/rubykan/Documents/CLOTH
git fetch origin cursor/github-actions-workflows
git switch cursor/github-actions-workflows
git pull origin cursor/github-actions-workflows
npm ci
npm run lint
npm run check
```

### Track 2: XAU Feature Slicing

Owner: XAU-focused agent.

Tasks:

1. Read `docs/XAU_DIRTY_FILES_TRIAGE.md`.
2. Choose one PR group only.
3. Create a new branch from `origin/main`.
4. Copy or reapply only the files in that group.
5. Run server tests plus syntax checks.

### Track 3: Commerce Production Merge Path

Owner: CLOTH-focused agent.

Tasks:

1. Confirm whether `cursor/github-actions-workflows` should become production main.
2. If yes, open/merge PR from `cursor/github-actions-workflows` to `main`.
3. After merge, run:

```bash
npm ci
npm run lint
npm run check
```

4. Then add live-selling integration tests.

## Current Blockers

| Blocker | Impact | Owner |
| --- | --- | --- |
| XAU dirty tree is large and mixed | High risk of one oversized unstable PR | XAU agent |
| CLOTH PR #6 base is not main | Production state ambiguous | CLOTH agent |
| Cross-repo XAU/CLOTH UI runtime still needs owner-specific verification | Medium | XAU/CLOTH agents |
| Supabase/Edge Function deployment status not verified in this pass | BuyerOS backend risk | BuyerOS/Supabase agent |

## Acceptance Checklist

Before calling Phase 2 stable:

- [ ] BuyerOS go-live audit passes after latest deployment.
- [ ] XAU `origin/main` server tests pass.
- [ ] CLOTH production target branch lint/check passes.
- [ ] XAU dirty tree is split into reviewed PR groups.
- [x] BuyerOS can call XAU and CLOTH runtime APIs through typed clients and dispatcher contracts.
- [ ] No fake engagement or fake social proof is introduced.
- [ ] No `.env`, token, private key, log, pid, cache, or build artifact is committed.
