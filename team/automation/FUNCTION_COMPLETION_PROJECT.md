# 三 Repo 功能完成專案書

Last updated: 2026-05-27
Owner: rubykan
Status: ACTIVE project definition

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` if executing this plan task-by-task. This document is the functional completion contract. Do not treat clean git, merged PRs, or automation dry-run PASS as feature completion.

## Goal

完成並驗收三條產品線的可用功能：

- `buyer_ai`: BuyerOS 買手 AI 中樞、任務派發、Context / Timeline / Report / Telegram mock / Ops UI
- `commerce`: CLOTH 網店營運、商品、訂單、庫存、財務、客服、篩選分頁、手機導航
- `xau`: XAU AI 直播系統、行情分析、三格信號、OBS overlay、會員頁、直播老師外觀、campaign / conversion / metrics

## Current Truth

- Repo hygiene green 只代表「暫時無 dirty / secret diff / deploy blocker」，不代表功能完成。
- 功能完成必須由「可點擊 UI + API / test evidence + user-facing workflow」共同證明。
- 上一輪 `multi-agent-system` 不是本專案；不要再把 prompt 系統當成功能專案。
- Canonical 三線仍然係：`buyer_ai / commerce / xau`。

## Repos

| Line | Repo | Local path |
|---|---|---|
| `buyer_ai` | BuyerOS | `/Users/rubykan/Downloads/buyeros-production-repo-v8` |
| `commerce` | CLOTH | `/Users/rubykan/Documents/CLOTH` |
| `xau` | XAU | `/Users/rubykan/Documents/XAU` |
| shared state | Team | `/Users/rubykan/Documents/team` |

## Hard Rules

- 不讀、不打印、不提交任何 `.env` value、token、service role key、private key。
- 不做 deploy / SSH / Supabase mutation / DB migration，除非 rubykan 明確講「deploy」。
- 不跨 repo 順手重構；跨線問題先記錄為 blocker。
- 不可以用「tests pass」單獨宣稱 UI 功能完成。
- 不可以用「PR merged」單獨宣稱產品完成。
- 每次完成一批功能，要更新 `/Users/rubykan/Documents/team/state.md` 和相關 `/Users/rubykan/Documents/team/projects/*.md`。

## Definition Of Done

一個功能只可標記 Done，如果同時滿足：

1. **UI 可見**：有可打開頁面、按鈕或清楚的 API-only 說明。
2. **操作可用**：主要按鈕不是空氣 button；click 後有成功、失敗或 blocked feedback。
3. **資料正確**：API response / store / DB state 與 UI 一致。
4. **測試覆蓋**：有自動化 test 或明確 manual smoke evidence。
5. **邊界正確**：不把 buyer_ai / commerce / xau 職責寫錯。
6. **git hygiene**：目標 repo 無 unrelated dirty、無 secret diff。

## Milestone 0：功能盤點與頁面索引

**Objective:** 先列清楚每個 repo 有咩頁面、功能、按鈕、API，避免「好多地方出錯」但無追蹤清單。

### Tasks

- [ ] **M0-1 BuyerOS UI map**
  - Repo: `/Users/rubykan/Downloads/buyeros-production-repo-v8`
  - Produce list of pages/routes:
    - `/`
    - `/#ops`
    - project switching
    - dispatch / run all
    - context / memory / timeline
    - report / promo / orchestration panel
  - Output file: `/Users/rubykan/Documents/team/projects/buyeros.md`
  - Acceptance: each route has status `PASS / FAIL / BLOCKED / NOT IMPLEMENTED`.

- [ ] **M0-2 CLOTH UI map**
  - Repo: `/Users/rubykan/Documents/CLOTH`
  - Produce list of pages/routes:
    - products list
    - product detail
    - cart
    - wishlist
    - orders
    - support
    - admin
    - inventory
    - finance
    - mobile nav
  - Output file: `/Users/rubykan/Documents/team/projects/cloth.md`
  - Acceptance: each route has API dependency and current smoke status.

- [ ] **M0-3 XAU UI map**
  - Repo: `/Users/rubykan/Documents/XAU`
  - Produce list of pages/routes:
    - dashboard
    - member dashboard
    - live dashboard
    - OBS scene / overlay
    - AI teacher appearance / wardrobe
    - signal cards
    - copy/manual prompt panel
    - campaign / promo / metrics pages
  - Output file: `/Users/rubykan/Documents/team/projects/xau.md`
  - Acceptance: each route has browser URL, known broken controls, and owner line.

### Validation

```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run
```

## Milestone 1：BuyerOS `buyer_ai` 可用閉環

**Objective:** BuyerOS 由「有 backend tests」提升到「UI 可操作的買手 AI 工作台」。

### Required Workflows

| ID | Workflow | Expected user-facing behavior |
|---|---|---|
| BAI-1 | Project switch | user can switch `buyer_ai / commerce / xau`; active project visibly changes |
| BAI-2 | Dispatch plan | user clicks dispatch; sees generated task plan or clear failure |
| BAI-3 | Run all | user clicks run all; sees progress/result for each step |
| BAI-4 | Context hub | user can view current context/memory/timeline |
| BAI-5 | Buyer report | user can generate/view buyer report without backend crash |
| BAI-6 | Telegram mock | works without real Telegram token; clear mock result |
| BAI-7 | Ops panel | no air buttons; each control has visible result/fallback |
| BAI-8 | Redis orchestration | agent state update + timeline + WebSocket echo work locally or show clear blocked state |

### Implementation Tasks

- [ ] **BAI-T1 Add UI smoke for main controls**
  - Target tests: BuyerOS frontend Playwright or existing UI smoke harness.
  - Cover: main buttons, project switch, theme switch, mobile overflow.
  - Fail condition: button click produces no DOM change, no toast, no network request, and no error state.

- [ ] **BAI-T2 Add ops smoke**
  - Cover `/#ops`.
  - Every ops control must either:
    - trigger a safe read-only endpoint, or
    - show `Not configured` / `Blocked` / `Mock mode` message.

- [ ] **BAI-T3 Verify runtime contracts**
  - Backend tests must cover:
    - `/projects`
    - `/tasks/dispatch_plan`
    - `/tasks/{id}/run_all`
    - `/memory/timeline`
    - orchestration state update
  - Required result shape: stable JSON with `ok`, `project`, `trace_id` or documented equivalent.

- [ ] **BAI-T4 Fix UI/API mismatch**
  - If UI expects a route that backend does not expose, either wire the route or change UI to the existing route.
  - Do not add fake green UI that hides backend errors.

- [ ] **BAI-T5 Update BuyerOS docs**
  - Docs must say refund / OCR / reconciliation / manual review belong to `buyer_ai`.
  - `commerce` only supplies operational data.

### Validation Commands

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short
cd frontend && npm run lint && npm run build
python3 /Users/rubykan/Documents/team/automation/run.py check --repo buyeros --dry-run
```

### Done Evidence

- Backend tests pass.
- Frontend lint/build pass.
- Browser smoke screenshots or log summary recorded in `/Users/rubykan/Documents/team/projects/buyeros.md`.
- No unresolved air buttons in main or ops UI.

## Milestone 2：CLOTH `commerce` 網店可用閉環

**Objective:** CLOTH 不只 API smoke 綠，要做到網店核心流程可點、可查、可驗。

### Required Workflows

| ID | Workflow | Expected user-facing behavior |
|---|---|---|
| COM-1 | Browse products | filtering, pagination, sort, search all work |
| COM-2 | Product detail | product data loads; market/status/stock badges correct |
| COM-3 | Cart | add/remove/update quantity works or clearly marked not implemented |
| COM-4 | Wishlist | add/remove/list works |
| COM-5 | Orders | create/list/order detail works |
| COM-6 | Finance | records/stats load; invalid numbers return 400 |
| COM-7 | Inventory | stock inbound/outbound works; invalid quantities return 400 |
| COM-8 | Support | FAQ/ticket/message flow works |
| COM-9 | Admin | admin routes load without blank state |
| COM-10 | Mobile nav | full-screen menu, close, route click, scroll lock work |

### Implementation Tasks

- [ ] **COM-T1 Complete API regression suite**
  - Required tests:
    - `scripts/api-smoke.test.mjs`
    - `scripts/products-filter-pagination.test.mjs`
    - `scripts/api-validation-errors.test.mjs`
    - `scripts/product-market-persistence.test.mjs`
    - `scripts/mobile-nav-contract.test.mjs`
    - `api/src/db/sqlite-store.test.ts`

- [ ] **COM-T2 Add UI smoke route list**
  - Cover products, cart, wishlist, orders, support, admin, finance, inventory.
  - A blank page, horizontal overflow, or console error is FAIL.

- [ ] **COM-T3 Mark missing features honestly**
  - If a flow is not implemented, record `NOT IMPLEMENTED` in `cloth.md`.
  - Do not rename missing features as complete.

- [ ] **COM-T4 Define commerce-to-buyer_ai data handoff**
  - Document payload fields for order, payment, refund source, inventory movement, support case.
  - No cross-repo mutation unless explicitly requested.

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

Note: `api-smoke.test.mjs` and `products-filter-pagination.test.mjs` both use a fixed port; run sequentially.

### Done Evidence

- Tests pass.
- UI smoke covers all required pages.
- `cloth.md` lists PASS/FAIL/BLOCKED for each workflow.
- No claim that CLOTH owns buyer_ai refund/OCR/reconciliation.

## Milestone 3：XAU 直播系統可用閉環

**Objective:** XAU 不只 dashboard 打開，要完整驗證直播、會員、OBS、三格信號、campaign/metrics。

### Required Workflows

| ID | Workflow | Expected user-facing behavior |
|---|---|---|
| XAU-1 | Dashboard | realtime price/analysis/grid cards load |
| XAU-2 | Three-grid cards | bullish/neutral/bearish active state correct |
| XAU-3 | Copy fallback | copy button works or manual copy panel appears |
| XAU-4 | Live overlay | price/grid/risk shown; draggable/autohide does not block UI |
| XAU-5 | OBS scene | loads without console errors |
| XAU-6 | Member dashboard | member-only UI routes work |
| XAU-7 | AI teacher appearance | wording is live avatar appearance, not CLOTH try-on |
| XAU-8 | Campaign / promo / metrics | APIs/pages produce visible result or marked not implemented |
| XAU-9 | TTS / script generation | missing config returns clear error; no crash |

### Implementation Tasks

- [ ] **XAU-T1 Add browser QA checklist**
  - Record all XAU pages and current URL.
  - Mark every broken control as FAIL with exact selector/text.

- [ ] **XAU-T2 Fix high-friction UI bugs first**
  - Inline `onclick` blocked by CSP.
  - Mobile horizontal overflow at 390px.
  - Empty buttons / no-feedback controls.

- [ ] **XAU-T3 Verify analysis engine**
  - `calculateXAUAnalysis()`
  - `buildGridCards()`
  - `analysis-output.test.js`

- [ ] **XAU-T4 Verify OBS/live**
  - Open OBS scene and overlay routes.
  - Console must be free of runtime errors.

- [ ] **XAU-T5 Verify feature boundary wording**
  - AI teacher wardrobe = live avatar appearance.
  - CLOTH customer try-on = commerce only.

### Validation Commands

```bash
cd /Users/rubykan/Documents/XAU
npm test
npm run test:server
node --test tests/analysis-output.test.js
python3 /Users/rubykan/Documents/team/automation/run.py check --repo xau --dry-run
```

### Done Evidence

- Tests pass.
- Browser smoke list recorded in `/Users/rubykan/Documents/team/projects/xau.md`.
- No blank/air-button controls remain in tested routes.
- XAU does not mutate CLOTH cart/orders/products.

## Milestone 4：Cross-Line Contract

**Objective:** 三線互相供應資料，但不混淆職責。

### Contract Table

| From | To | Allowed data | Forbidden |
|---|---|---|---|
| commerce | buyer_ai | orders, payment refs, inventory movements, support cases | owning refund/OCR/reconciliation/manual review |
| xau | buyer_ai | campaign, lead, conversion, metrics, transcript references | direct buyer purchase execution unless dispatched |
| buyer_ai | commerce | buyer instructions, report refs, reconciliation result | silent product/cart mutation |
| buyer_ai | xau | campaign brief, script context, metrics request | mutating live signal state without XAU API |

### Checks

- [ ] Search docs for incorrect ownership wording.
- [ ] Search code for direct cross-repo API assumptions.
- [ ] Record all intended integration endpoints before implementation.

## Milestone 5：Final Acceptance

**Objective:** 只有完成以下全部，先可以講「專案收口」。

### Required Final Commands

```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run
```

BuyerOS:
```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short
cd frontend && npm run lint && npm run build
```

CLOTH:
```bash
cd /Users/rubykan/Documents/CLOTH
npm run lint
npm run check
node --test scripts/api-smoke.test.mjs
node --test scripts/products-filter-pagination.test.mjs
node --test scripts/api-validation-errors.test.mjs
node --test scripts/product-market-persistence.test.mjs
node --test scripts/mobile-nav-contract.test.mjs
node --import tsx --test api/src/db/sqlite-store.test.ts
```

XAU:
```bash
cd /Users/rubykan/Documents/XAU
npm test
npm run test:server
node --test tests/analysis-output.test.js
```

### Required Reports

- `/Users/rubykan/Documents/team/state.md`
- `/Users/rubykan/Documents/team/projects/buyeros.md`
- `/Users/rubykan/Documents/team/projects/cloth.md`
- `/Users/rubykan/Documents/team/projects/xau.md`
- `/Users/rubykan/Documents/team/automation/latest-report.md`

Each report must include:

- Completed workflows.
- Failed workflows.
- Not implemented workflows.
- Blockers.
- Exact validation commands and latest result.
- Browser/UI evidence summary.

## Handoff Prompt

```text
請先讀：
- /Users/rubykan/Documents/team/state.md
- /Users/rubykan/Documents/team/automation/FUNCTION_COMPLETION_PROJECT.md
- /Users/rubykan/Documents/team/projects/buyeros.md
- /Users/rubykan/Documents/team/projects/cloth.md
- /Users/rubykan/Documents/team/projects/xau.md

今次不是 multi-agent prompt system。
今次專案是三 repo 功能完成：buyer_ai / commerce / xau。

最高規則：
- 回覆用廣東話。
- 開始前先跑目標 repo 的 `git status --short`。
- 不要讀、打印、提交任何 secret 或 .env value。
- 不要 deploy / SSH / Supabase mutation / DB migration，除非 rubykan 明確要求。
- 不要跨 repo 亂改；跨線問題先記錄 blocker。
- 不要把 repo hygiene / PR merged 當成功能完成。
- 每個功能要有 UI/API/test evidence。

建議第一步：
做 Milestone 0 功能盤點，然後做 Milestone 1 BuyerOS buyer_ai 可用閉環。
交付：PASS / FAIL / BLOCKED / NOT IMPLEMENTED 清單、修復項、驗收命令、測試結果。
```

## Immediate Next Step

Start with Milestone 0, then Milestone 1:

1. Build BuyerOS UI/API map.
2. Identify every air button / missing route.
3. Fix BuyerOS main + ops flows before moving to CLOTH/XAU.
4. Update shared state after each validated batch.
