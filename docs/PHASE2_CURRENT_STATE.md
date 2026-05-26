# Phase 2 Current State

Last verified: 2026-05-25

This file records the current state of the three-system Phase 2 work so parallel AI agents do not repeat completed tasks or touch the wrong branch.

## Canonical Systems

| System | Canonical ID | Repo | Role |
| --- | --- | --- | --- |
| Buyer AI 中樞 | `buyer_ai` | `/Users/rubykan/Downloads/buyeros-production-repo-v8` | BuyerOS, AI Team, Context Hub, Telegram, buyer report, sourcing ROI, refund reconciliation, OCR posting, manual review |
| Commerce 網店自動系統 | `commerce` | `/Users/rubykan/Documents/CLOTH` | Orders, after-sales source data, inventory, support, shop finance, live-selling flow |
| XAU 系統 | `xau` | `/Users/rubykan/Documents/XAU` | AI live stream, real-time news, script generation, OBS, campaign/conversion |

Boundary note: refund reconciliation, refund matching, OCR posting, and manual review belong to `buyer_ai`.
`commerce` only supplies webshop order, after-sales, payment, inventory, and support data for reconciliation.

## PR And Branch State

| Repo | PR | State | Merge Commit | Notes |
| --- | --- | --- | --- | --- |
| XAU | `uugiftcard-sudo/XAU#3` | merged | `c7851e9` | Merged into `main`. Fresh server test passed after merge. |
| CLOTH | `uugiftcard-sudo/ai-luxury-resale-os#6` | merged | `d4512c1` | Merged into `cursor/github-actions-workflows`, not confirmed merged into `main`. |
| BuyerOS | `uugiftcard-sudo/buyeros-production-repo-v8#11` | merged | `992cde3` | Merged into `main`; production deployment/audit had passed in prior run. |

## Local Repo State

### BuyerOS

- Path: `/Users/rubykan/Downloads/buyeros-production-repo-v8`
- Current branch at verification time: `main`, then this documentation branch `codex/phase2-handoff-triage`
- Dirty state before documentation work: clean
- Safe for coordination docs and smoke/audit work.

### CLOTH

- Path: `/Users/rubykan/Documents/CLOTH`
- Current branch: `codex/ai-live-commerce-v1`
- Dirty state: clean
- Important: PR #6 was merged into `cursor/github-actions-workflows`; before any production work, confirm whether that branch should merge into `main`.

### XAU

- Path: `/Users/rubykan/Documents/XAU`
- Current branch: `codex/ai-live-commerce-v1`
- Dirty state: not clean
- Do not bulk commit. See `docs/XAU_DIRTY_FILES_TRIAGE.md`.

## Verified Commands And Results

### XAU

Fresh verification was run against merged `origin/main` after PR #3:

```bash
cd /tmp/xau-pr3-check/server
npm test
```

Result:

```text
tests 18
pass 18
fail 0
```

### CLOTH

Fresh verification was run against merged `origin/cursor/github-actions-workflows` after PR #6:

```bash
cd /tmp/cloth-pr6-check
npm ci
npm run lint
npm run check
```

Result:

```text
lint: 0 errors, 7 warnings
build/typecheck: passed
```

Known warnings:

```text
api/src/index.ts console statements
api/src/middleware/response.ts console statement
```

## What Is Already Done

1. Phase 1 PR merge work is no longer pending for XAU, CLOTH PR #6, or BuyerOS PR #11.
2. XAU server import crash from missing TTS route was fixed in PR #3 before merge.
3. BuyerOS production branch had already passed go-live audit in the previous run.
4. BuyerOS Phase 2 runtime contract coverage now proves:
   - XAU typed client calls `GET /api/news/latest` and `POST /api/ai/script`
   - CLOTH typed client calls `GET /api/live/readiness` and `POST /api/live/selling-plan`
   - Dispatcher completes configured `xau` subtasks through `xau_integration`
   - Dispatcher completes configured `commerce` live-selling subtasks through `cloth_integration`

## What Is Still Not Done

1. CLOTH merged code is not confirmed on `main`.
2. XAU local dirty live-stream/OBS/avatar/analytics work is not triaged into clean PRs.
3. Cross-repo UI/runtime behavior outside BuyerOS still needs owner-specific verification:
   - XAU live script/news rendering in live room/app
   - Commerce product/inventory/finance behavior inside CLOTH live-selling UI
4. Supabase/Edge Function items in the Cursor plan may still require human/project-level verification; do not assume they are complete from plan text.

## Recommended Next Sequence

1. XAU: triage dirty files into safe PR groups.
2. CLOTH: decide and execute merge path from `cursor/github-actions-workflows` to `main`.
3. BuyerOS: keep `backend/tests/test_integration_routing.py` green for XAU/CLOTH runtime client and dispatcher contracts.
4. Monitoring: record one fresh BuyerOS go-live audit after any new production deploy.

## Fast Verification Commands

```bash
cd /Users/rubykan/Documents/XAU
git fetch origin main
git status --short
git log --oneline origin/main -3
```

```bash
cd /Users/rubykan/Documents/CLOTH
git fetch origin cursor/github-actions-workflows main
git status --short
git log --oneline origin/cursor/github-actions-workflows -3
```

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
git fetch origin main
git status --short
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests/test_integration_routing.py -v --tb=short
./infra/go_live_audit.sh .env.production.local https://buyeros.206.189.116.155.sslip.io root@206.189.116.155 root@167.172.60.38
```
