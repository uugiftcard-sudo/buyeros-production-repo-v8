# AI Collaboration Plan — BuyerOS / XAU / CLOTH

Last updated: 2026-05-27
Owner: rubykan
Primary coordination source:
- `/Users/rubykan/Documents/team/state.md`
- `/Users/rubykan/Documents/team/agents.md`
- `/Users/rubykan/Documents/team/projects/buyeros.md`
- `/Users/rubykan/Documents/team/projects/cloth.md`
- `/Users/rubykan/Documents/team/projects/xau.md`
- `/Users/rubykan/Documents/team/projects/three-repo-automation.md`

## Highest Priority Rules

1. Always read shared state before touching code.
2. Always run `git status --short` in the target repo before making changes.
3. Do not overwrite, revert, stage, commit, deploy, or push changes you did not make unless rubykan explicitly asks.
4. Never print, copy, commit, or infer secret values from `.env`, private keys, tokens, or service role keys.
5. No production deploy, SSH, Supabase mutation, DB migration, or external API mutation unless the task explicitly says to do that.
6. Keep work scoped. If a bug belongs to another repo, record it as a blocker instead of editing across repos.
7. Reply in Cantonese unless rubykan asks otherwise.

## Current Repo Map

### BuyerOS

Repo:
- `/Users/rubykan/Downloads/buyeros-production-repo-v8`

Current branch:
- `codex/buyeros-redis-orchestration-clean`

Current status:
- Redis orchestration clean draft PR open: `https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/pull/19`
- Backend pytest previously passed: 234 tests.
- UI smoke previously passed.
- Automation dry-run currently reports PASS, dirty=no, secret diff=no, deploy gate=open.

Canonical system boundaries:
- `buyer_ai`: BuyerOS / AI Team / Context Hub / Telegram / Task Dispatcher / buyer reports / refund reconciliation / OCR posting / manual review.
- `commerce`: webshop orders / after-sales / payment / inventory / support / shop finance / live selling; supplies data to `buyer_ai` but does not own buyer refund reconciliation.
- `xau`: XAU AI live stream / real-time news / script generation / OBS / promo / campaign / conversion / metrics.

Important files:
- `backend/app/orchestration.py`
- `backend/app/workflows/main.py`
- `backend/tests/test_orchestration.py`
- `frontend/`
- `docs/`
- `infra/`

Do next:
- Review PR #19 scope and CI status if network/GitHub is available.
- If asked to continue BuyerOS, focus on PR #19 review fixes only.
- Do not reopen old PR #18.
- Do not mix Phase 4/5/6 commits into Redis PR.

Validation commands:
```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short
cd frontend && npm run lint && npm run build
```

Automation check:
```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo buyeros --dry-run
```

## XAU

Repo:
- `/Users/rubykan/Documents/XAU`

Current branch:
- `codex/xau-dashboard-live-ui`

Current status:
- XAU marked completed in shared state.
- Dev server usually: `http://127.0.0.1:3002/`
- Automation dry-run currently reports PASS, dirty=no, secret diff=no, deploy gate=open.
- Production deploy target is not defined. Automation deploy is local Docker only.

Important pages for manual QA:
- `http://127.0.0.1:3002/`
- `http://127.0.0.1:3002/features/member/dashboard.html?clientId=demo`
- `http://127.0.0.1:3002/features/avatar-wardrobe/wardrobe.html`
- `http://127.0.0.1:3002/promo-v2/poster-v2.html`
- `http://127.0.0.1:3002/stream/obs-scene.html`
- `http://127.0.0.1:3002/stream/obs-control-panel.html`
- `http://127.0.0.1:3002/health`

Important files:
- `app.js`
- `stream/live-engine.js`
- `stream/obs-scene.html`
- `stream/obs-control-panel.html`
- `server/routes/tts.js`
- `tests/analysis-output.test.js`

Do next:
- Only fix explicit QA issues rubykan reports.
- Keep live avatar / wardrobe copy separate from CLOTH customer try-on.
- Do not restore `.env`, runtime DB, generated signal data, or old `server/data/*`.

Validation commands:
```bash
cd /Users/rubykan/Documents/XAU
npm run test:server
node --test tests/analysis-output.test.js
```

Automation check:
```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo xau --dry-run
```

## CLOTH

Repo:
- `/Users/rubykan/Documents/CLOTH`

Current branch:
- `codex/cloth-phase2-products-filter`

Current status:
- Phase 0 complete: SQLite persistence for product/order/finance/inventory/support.
- Phase 1 complete: mobile nav, market persistence, validation/error handling, API smoke contracts.
- Phase 2 P2-A opened: products filtering + pagination.
- Automation dry-run currently reports PASS, dirty=no, secret diff=no, deploy gate=open.
- Branch is still ahead 2 in automation report; this is not a dirty blocker, but should be pushed/PR-checked when network is available.

Important docs:
- `/Users/rubykan/Documents/CLOTH/docs/PHASE_2_CONTRACT.md`

Important routes:
- `api/src/routes/products.ts`
- `api/src/routes/orders.ts`
- `api/src/routes/finance.ts`
- `api/src/routes/inventory.ts`
- `api/src/routes/support.ts`

Important tests:
- `scripts/api-smoke.test.mjs`
- `scripts/api-validation-errors.test.mjs`
- `scripts/product-market-persistence.test.mjs`
- `scripts/products-filter-pagination.test.mjs`
- `scripts/mobile-nav-contract.test.mjs`
- `api/src/db/sqlite-store.test.ts`

Do next:
- Review/push/PR-check Phase 2 products filtering branch if asked.
- Do not expand Phase 2 into auth, wishlist, finance, inventory, support, or UI redesign unless rubykan explicitly asks.
- Real CLOTH deploy still needs VPS/nginx/systemd validation and DNS reachability.

Validation commands:
```bash
cd /Users/rubykan/Documents/CLOTH
npm run check
npm run lint
node --test scripts/api-smoke.test.mjs
node --test scripts/api-validation-errors.test.mjs
node --test scripts/product-market-persistence.test.mjs
node --test scripts/products-filter-pagination.test.mjs
node --test scripts/mobile-nav-contract.test.mjs
node --import tsx --test api/src/db/sqlite-store.test.ts
```

Automation check:
```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo cloth --dry-run
```

## Shared Automation Controller

Path:
- `/Users/rubykan/Documents/team/automation/`

Primary command:
```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run
```

Expected latest dry-run status:
- BuyerOS: PASS, dirty=no, secret diff=no, deploy gate=open.
- XAU: PASS, dirty=no, secret diff=no, deploy gate=open.
- CLOTH: PASS, dirty=no, secret diff=no, deploy gate=open.
- CLOTH branch ahead 2 is a PR hygiene note, not a deploy blocker.

Rules:
- `check --dry-run` may be run freely.
- Do not run `deploy` unless rubykan explicitly asks for deploy mode.
- Production deploy should never be scheduled automatically.
- If check shows dirty tree or secret diff, stop and report the exact repo and blocker.

## Suggested Work Split For Another AI

The second AI should work as a verifier/reviewer, not an uncontrolled implementer.

## Function Completeness Requirement

rubykan's explicit requirement: do not only check the home page or the currently open screen. The assistant must remember and preserve the full previously discussed feature set. QA and implementation must be feature-complete across all three products.

### BuyerOS feature surface to preserve/check

- Main dashboard controls.
- `#ops` operations controls.
- Dispatch flow.
- Project switch.
- Theme switch.
- Mobile overflow and responsive layout.
- Redis orchestration runtime:
  - `POST /api/v1/orchestration/state-update`
  - `GET /api/v1/orchestration/agent/{agent_id}`
  - `GET /api/v1/orchestration/trace/{trace_id}/timeline`
  - `WS /ws/trace/{trace_id}`
  - history echo on WebSocket connect.
- Three-line runtime boundary:
  - `buyer_ai`
  - `commerce`
  - `xau`
- Buyer AI features remain separate from commerce:
  - refund reconciliation
  - OCR posting
  - manual review
  - buyer report
  - task dispatcher
  - Telegram/context hub integration.
- Do not merge old Phase 4/5/6 commits into Redis-only PR scope.

### XAU feature surface to preserve/check

- Dashboard live ops UI.
- AI analysis output / `calculateXAUAnalysis()`.
- Three grid signal cards: up / neutral / down.
- Active grid state and risk display.
- Copy fallback and manual copy panel.
- Live overlay.
- OBS pages:
  - `stream/obs-scene.html`
  - `stream/obs-control-panel.html`
  - `stream/obs-panel.html`
  - `stream/obs-studio.html`
  - `stream/janus-embed.html`
  - `stream/admin.html`
- Promo/poster pages:
  - `promo-v2/poster-v2.html`
  - `promo/poster.html`
- Quiz page.
- Member dashboard.
- Avatar wardrobe is for XAU live AI teacher appearance only.
- Do not confuse XAU wardrobe with CLOTH customer try-on.
- Do not restore `.env`, runtime DB, generated signals, or old data files.

### CLOTH feature surface to preserve/check

- Products listing.
- Product filtering and pagination:
  - market
  - status
  - brand
  - category
  - condition
  - minPrice/maxPrice
  - search
  - page/limit
  - sort
- Product create/update/delete.
- Product market persistence.
- Orders.
- Cart.
- Wishlist.
- Support / FAQ.
- Admin routes.
- Warehouse / inventory.
- Finance.
- Mobile navigation:
  - full-screen overlay
  - backdrop
  - body scroll lock
  - Escape close
  - route-click close
  - cart badge
  - admin/ops grouping
- SQLite persistence for products/orders/finance/inventory/support.
- Input validation and structured JSON errors.
- CLOTH customer AI try-on belongs to CLOTH/webshop, not XAU live avatar clothing.

### QA rule

When rubykan says "全部塞晒畀我睇", "全面檢查", "功能完全", or similar, provide or execute a full checklist across the above feature surfaces. Do not answer with only one URL or one page.

### Lane A — UI / Manual QA Assistant

Goal:
- Help rubykan inspect BuyerOS, XAU, and CLOTH pages and record broken buttons, missing flows, layout overflow, console errors, or wrong copy.

Rules:
- Use browser/manual QA only first.
- Do not edit code until a reproducible issue is written down.
- For each issue, record URL, viewport, click path, expected behavior, actual behavior, console error, and screenshot if possible.

Deliverable:
- Short issue list grouped by repo.
- Each issue should include a suggested owner: BuyerOS / XAU / CLOTH / shared automation.

### Lane B — PR Hygiene Assistant

Goal:
- Check open branch/PR cleanliness and avoid mixed PRs.

Rules:
- Run read-only git commands first.
- Do not stage/commit/push unless rubykan explicitly asks.
- Confirm PR diff does not include `.env`, runtime DBs, generated logs, build output, or unrelated repo changes.

Useful commands:
```bash
git status --short
git branch --show-current
git log --oneline --decorate -10
git diff --stat
git diff | rg -n "(sk-|service_role|TELEGRAM_BOT_TOKEN|SUPABASE_KEY|OPENROUTER_API_KEY|ANTHROPIC_API_KEY)" || true
```

### Lane C — Test Runner Assistant

Goal:
- Run validation commands for one repo at a time and summarize pass/fail.

Rules:
- Never run deploy scripts.
- Never run commands that upload secrets.
- If a command fails, capture only safe error text and propose the smallest fix.

Deliverable format:
```markdown
## Repo
- Branch:
- Status:
- Commands run:
- Passed:
- Failed:
- Blockers:
- Next smallest fix:
```

## Current Best Next Actions

1. BuyerOS: review PR #19 and merge if CI/review passes.
2. CLOTH: push/check Phase 2 branch if not already pushed; verify PR #9 status.
3. XAU: only fix concrete UI/QA issues reported by rubykan.
4. Automation: keep heartbeat check as read-only monitor; do not deploy automatically.

## Handoff Prompt To Paste To Another AI

```text
你係第二個協作 AI。請先讀：
- /Users/rubykan/Documents/team/state.md
- /Users/rubykan/Documents/team/agents.md
- /Users/rubykan/Documents/team/ai-collaboration-plan.md
- /Users/rubykan/Documents/team/projects/buyeros.md
- /Users/rubykan/Documents/team/projects/cloth.md
- /Users/rubykan/Documents/team/projects/xau.md
- /Users/rubykan/Documents/team/projects/three-repo-automation.md

最高規則：
- 回覆用廣東話。
- 開始前先跑目標 repo 的 `git status --short`。
- 不要改、stage、commit、push、deploy、SSH、Supabase mutation，除非 rubykan 明確叫你做。
- 不要讀出、打印、複製、提交任何 `.env`、token、private key、service role key。
- 不要跨 repo 亂改。發現其他 repo 問題，只記錄 blocker。
- 不要重做已完成工作。

目前狀態：
- BuyerOS：Redis orchestration clean draft PR #19，branch `codex/buyeros-redis-orchestration-clean`，待 review/merge。
- XAU：branch `codex/xau-dashboard-live-ui`，目前 automation PASS，主要等用家逐頁 QA 後再修具體問題。
- CLOTH：branch `codex/cloth-phase2-products-filter`，Phase 2 products filtering/pagination 已做，automation PASS，但 branch ahead 2，需要 PR/push/review 狀態確認。
- Shared automation：`python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run` 目前三 repo PASS/open。

你今次任務：
1. 做 read-only 狀態核對。
2. 幫 rubykan 做 UI/功能 QA 或 PR hygiene review。
3. 將發現按 BuyerOS / XAU / CLOTH 分組。
4. 每個問題寫 URL、重現步驟、預期、實際、嚴重程度、建議下一步。
5. 完成後簡短回報，必要時更新 /Users/rubykan/Documents/team/projects/ 對應 project md，但不要寫入任何 secret。
```
