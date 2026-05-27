# 三線功能補齊計劃：buyer_ai / commerce / xau

Last updated: 2026-05-27
Owner: rubykan
Status: ACTIVE detailed project plan

## Summary
按「三線全部」補齊，分三批做。第一批補 `buyer_ai` 買手底座；第二批補 `commerce` 真網店營運流；第三批補 `xau` campaign/metrics。退款對帳、退款比對、OCR 入帳、manual review 主責歸 `buyer_ai`，`commerce` 只提供網店訂單、售後、支付、庫存、客服資料作為比對來源。

## Source Of Truth

Shared state:
- `/Users/rubykan/Documents/team/state.md`
- `/Users/rubykan/Documents/team/projects/buyeros.md`
- `/Users/rubykan/Documents/team/projects/cloth.md`
- `/Users/rubykan/Documents/team/projects/xau.md`
- `/Users/rubykan/Documents/team/projects/three-repo-automation.md`

Repos:
- BuyerOS: `/Users/rubykan/Downloads/buyeros-production-repo-v8`
- CLOTH / commerce: `/Users/rubykan/Documents/CLOTH`
- XAU: `/Users/rubykan/Documents/XAU`

Automation:
- `/Users/rubykan/Documents/team/automation/run.py`
- Safe monitor: `python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run`

## Hard Boundaries

- `buyer_ai` owns: BuyerOS / AI 中樞 / Context Hub / Telegram / Task Dispatcher / 買手 Report / 採購 ROI / refund reconciliation / refund matching / OCR posting / manual review.
- `commerce` owns: webshop order / after-sales / payment / inventory / support / shop finance / live selling. It only supplies operational data to `buyer_ai`; it does not own refund reconciliation, OCR posting, or manual review.
- `xau` owns: XAU AI live stream / real-time news / script generation / OBS / promo / campaign / conversion / metrics.
- XAU wardrobe/member appearance is AI teacher/live avatar styling, not CLOTH customer try-on.
- CLOTH customer try-on belongs to commerce/webshop, not XAU.
- No secrets, `.env`, private keys, service role keys, tokens, runtime DBs, generated logs, or build outputs may be committed.
- No production deploy, SSH, Supabase mutation, DB migration, or Edge Function deploy unless rubykan explicitly triggers deployment.

## Work Order

Do not start all three lines at once. Work in this order:

1. `buyer_ai` foundation and runtime contracts.
2. `commerce` operational data chain and CLOTH verification.
3. `xau` campaign/metrics loop and memory/timeline handback.
4. Cross-line isolation checks.
5. Final report and shared-state sync.

## Milestone 1：buyer_ai 買手底座

### Objective

Make BuyerOS the canonical `buyer_ai` runtime foundation for project listing, task dispatch, report/timeline, Telegram mock, refund/OCR/reconciliation boundaries, and ops status.

### Scope

- 修正文檔邊界：`buyer_ai` 代表 BuyerOS / AI 中樞 / Context Hub / Telegram / 買手 Report / 採購 ROI / 退款 / OCR / 對帳 / reconciliation / manual review
- 補齊 smoke 驗收：`/projects`、`/tasks/dispatch_plan`、`/tasks/{id}/run_all`、`/memory/timeline`、Telegram mock、ops status
- 更新受影響文檔：`GO_LIVE_EVIDENCE.md`、`PHASE2_CURRENT_STATE.md`、`THREE_WORKSPACE_GO_LIVE_PLAN.md`、`PHASE2_HANDOFF_FOR_CURSOR.md`、`SHOPS_SETUP.md`、`infra/README.md`

### Concrete Tasks

| ID | Task | Repo | Files / Area | Acceptance |
|---|---|---|---|---|
| BAI-1 | Confirm `/projects` canonical three-line response | BuyerOS | backend routes/tests | Returns only `buyer_ai`, `commerce`, `xau` |
| BAI-2 | Confirm dispatch plan contract | BuyerOS | task dispatcher | `/tasks/dispatch_plan` produces buyer_ai-scoped plan |
| BAI-3 | Confirm `run_all` integration smoke | BuyerOS | task runner | `/tasks/{id}/run_all` returns stable success/failure JSON |
| BAI-4 | Confirm memory timeline handback | BuyerOS | memory/timeline | `/memory/timeline` records buyer_ai events |
| BAI-5 | Confirm Telegram mock does not require real token | BuyerOS | Telegram mock/tests | Test passes without production token |
| BAI-6 | Confirm ops status reflects runtime health | BuyerOS frontend/backend | `#ops`, health endpoints | Ops controls show visible result/fallback |
| BAI-7 | Update docs boundary wording | BuyerOS docs | listed docs | No doc says refund/OCR/reconciliation belongs to commerce |

### Validation Commands

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short
cd frontend && npm run lint && npm run build
python3 /Users/rubykan/Documents/team/automation/run.py check --repo buyeros --dry-run
```

### Completion Evidence

- Test output showing backend tests pass.
- Frontend lint/build pass.
- Static doc search confirms canonical wording.
- Shared state updated with current branch/PR status and blockers.

## Milestone 2：commerce 網店自動系統

### Objective

Make CLOTH the verified commerce data source for orders, after-sales/support, payment/finance, inventory, and support. It must feed buyer_ai data, but not own buyer_ai reconciliation logic.

### Scope

- 補齊第一條真營運鏈：order / after-sales / payment / inventory / support → 提供資料給 `buyer_ai` refund/OCR/reconciliation → report/timeline
- 明確 `commerce` 負責：訂單、庫存、客服、網店收支、Shopify/TikTok/Custom API、AI live selling
- 明確 `commerce` 不主責：退款對帳、退款比對、OCR 入帳、manual review
- 檢查 CLOTH 現有 API：finance/inventory/support/wishlist/mobile nav

### Concrete Tasks

| ID | Task | Repo | Files / Area | Acceptance |
|---|---|---|---|---|
| COM-1 | Verify products filtering/pagination | CLOTH | `api/src/routes/products.ts` | `products-filter-pagination.test.mjs` passes |
| COM-2 | Verify orders API and page behavior | CLOTH | orders route/web | API smoke passes; browser QA still required |
| COM-3 | Verify finance as shop finance only | CLOTH | finance route/web | Finance does not claim refund reconciliation ownership |
| COM-4 | Verify inventory stock flow | CLOTH | inventory route/web | inbound/outbound smoke passes |
| COM-5 | Verify support/after-sales flow | CLOTH | support route/web | ticket/FAQ smoke passes |
| COM-6 | Verify mobile nav and market persistence | CLOTH | web/components + products route | contract tests pass |
| COM-7 | Define commerce-to-buyer_ai handoff payload | BuyerOS + CLOTH docs | docs / tests | Payload fields documented; no cross-repo mutation yet unless requested |

### Validation Commands

```bash
cd /Users/rubykan/Documents/CLOTH
npm run check
npm run lint
node --test scripts/mobile-nav-contract.test.mjs
node --test scripts/product-market-persistence.test.mjs
node --test scripts/api-validation-errors.test.mjs
node --import tsx --test api/src/db/sqlite-store.test.ts
node --test scripts/api-smoke.test.mjs
node --test scripts/products-filter-pagination.test.mjs
python3 /Users/rubykan/Documents/team/automation/run.py check --repo cloth --dry-run
```

Important:
- `api-smoke.test.mjs` and `products-filter-pagination.test.mjs` both use `PORT=3499`; run them sequentially, not in parallel.

### Completion Evidence

- Static tests pass.
- API smoke 26 cases pass.
- Products filter pagination 2 cases pass.
- Browser/UI QA result recorded separately before claiming UI complete.

## Milestone 3：xau 系統

### Objective

Keep XAU independent while providing campaign/conversion/metrics and memory/timeline handback to BuyerOS where explicitly designed.

### Scope

- 驗證 XAU `server/routes/wechat.js` crash fix 已穩定
- 補 campaign/conversion/metrics 最小閉環
- 保持 XAU 獨立，任務狀態回寫 BuyerOS memory/timeline

### Concrete Tasks

| ID | Task | Repo | Files / Area | Acceptance |
|---|---|---|---|---|
| XAU-1 | Confirm server/root tests | XAU | tests/server | test suite passes |
| XAU-2 | Confirm analysis output contract | XAU | `tests/analysis-output.test.js` | analysis output test passes |
| XAU-3 | Confirm dashboard and three-grid behavior | XAU | `app.js`, dashboard UI | browser QA passes |
| XAU-4 | Confirm OBS/live overlay pages | XAU | `stream/` | pages load without console errors |
| XAU-5 | Confirm campaign/conversion/metrics API | XAU | campaign routes/tests | endpoint returns stable JSON |
| XAU-6 | Confirm XAU does not trigger buyer_ai purchase flow | XAU + BuyerOS boundary | docs/tests/browser QA | no cross-line action unless explicitly dispatched |

### Validation Commands

```bash
cd /Users/rubykan/Documents/XAU
npm test
npm run test:server
node --test tests/analysis-output.test.js
python3 /Users/rubykan/Documents/team/automation/run.py check --repo xau --dry-run
```

### Completion Evidence

- XAU tests pass.
- XAU browser QA pages verified.
- Boundary checks recorded: XAU signals do not trigger buyer_ai purchase flow; XAU wardrobe is not CLOTH try-on.

## Milestone 4：Cross-Line Isolation

### Objective

Prove the three canonical lines can be reasoned about independently and do not leak state or ownership.

### Checks

| ID | Check | Acceptance |
|---|---|---|
| ISO-1 | `buyer_ai` crash/blocked state does not imply commerce ownership changes | docs/tests show commerce remains data provider |
| ISO-2 | `commerce` cart/order state is not read by XAU | no XAU code/API calls CLOTH cart unless explicitly designed |
| ISO-3 | XAU signal does not trigger buyer_ai purchase flow | no implicit purchase/dispatch side effect |
| ISO-4 | XAU wardrobe does not mutate CLOTH products/cart/orders | browser/API before-after evidence |
| ISO-5 | Refund/OCR/reconciliation/manual review all belong to buyer_ai | doc search proves wording |

## Execution Rules For Any AI

Before editing:
```bash
git status --short
git branch --show-current
```

If product repo is dirty:
- Stop and report dirty files.
- Do not revert.
- Do not stack unrelated work on top.

If touching docs only:
- Say no tests required only if no code changed.
- Still run `git diff --check`.

If touching code:
- Run the repo-specific validation commands above.

If touching shared state:
- Update `/Users/rubykan/Documents/team/state.md`.
- Update the relevant `/Users/rubykan/Documents/team/projects/*.md`.

## Handoff Prompt For Another AI

```text
請先讀：
- /Users/rubykan/Documents/team/state.md
- /Users/rubykan/Documents/team/automation/TRI_REPO_PLAN.md
- /Users/rubykan/Documents/team/projects/buyeros.md
- /Users/rubykan/Documents/team/projects/cloth.md
- /Users/rubykan/Documents/team/projects/xau.md

今次專案不是 multi-agent prompt system。
今次專案是三線功能補齊：buyer_ai / commerce / xau。

最高規則：
- 回覆用廣東話。
- 開始前先跑目標 repo 的 `git status --short`。
- 不要讀、打印、提交任何 secret 或 .env value。
- 不要 deploy / SSH / Supabase mutation / DB migration，除非 rubykan 明確要求。
- 不要跨 repo 亂改；跨線問題先記錄 blocker。
- 不要把退款/OCR/對帳/reconciliation/manual review 寫成 commerce 負責；它們屬於 buyer_ai。

建議先做 Milestone 1：buyer_ai 買手底座。
交付：清楚列出完成項、未完成項、驗收命令、測試結果、剩餘 blocker。
```

## Test Plan

Minimum final verification:

```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run
```

BuyerOS:
```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short
cd frontend && npm run lint && npm run build
```

Commerce / CLOTH:
```bash
cd /Users/rubykan/Documents/CLOTH
npm run lint
npm run check
node --test scripts/api-smoke.test.mjs
node --test scripts/products-filter-pagination.test.mjs
```

XAU:
```bash
cd /Users/rubykan/Documents/XAU
npm test
npm run test:server
node --test tests/analysis-output.test.js
```

## Acceptance Criteria
- Docs 裡再無「退款/OCR/對帳屬 commerce 或 BuyerOS 共用能力」文案
- Docs 明確寫出「退款/OCR/對帳/reconciliation/manual review 屬 `buyer_ai`」
- Docs 明確寫出「`commerce` 只提供網店資料來源」
- `/projects` 只返回 canonical 三線：`buyer_ai / commerce / xau`
- `buyer_ai` automation 能跑退款/OCR/對帳 smoke
- CLOTH commerce API 前端 build/lint/test 通過
- XAU server/root tests 通過
- 不提交 secrets、不改 production env、不做 dirty deploy
