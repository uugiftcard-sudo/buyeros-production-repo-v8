# CLOTH Project Detail

## 係咩
CLOTH 係一個 internal REST API + Web UI，包含 products/orders/finance/inventory/support 模組，用 SQLite 做持久化。

## Phase 0 ✅ COMPLETED（2026-05-25）

### 已實作
| 模組 | 檔案 | 狀態 |
|------|------|------|
| SQLite persistence | `api/src/db/index.ts` | ✅ |
| Migration | `api/src/db/migrations/001_initial.sql` | ✅ |
| Product/Order store | `api/src/models/store.ts` | ✅ |
| Finance API | CRUD + stats | ✅ |
| Inventory API | items + transactions + inbound/outbound | ✅ |
| Support API | tickets + messages + FAQs | ✅ |
| `.gitignore` | `api/data/` 不入 repo | ✅ |
| Dependencies | `better-sqlite3` + `@types/better-sqlite3` | ✅ |

### 驗收結果
- SQLite test：3 passed
- `npm run lint`：pass，7 個 console warnings（未超 repo 設定）
- `npm run check`：API + web build pass
- Smoke test 全部正常：
  - Product：POST 後重啟 server 仍讀得返
  - Finance：POST / stats / PUT / DELETE 正常，重啟後讀得返
  - Inventory：新增 SKU + inbound 後重啟，stock + transaction 仍存在
  - Support：開 ticket + agent message 後重啟，ticket 狀態同 message 仍存在
- 所有 smoke test 臨時 DB 檔已刪除

## Phase 1 ✅ COMPLETED — Stabilise API + Web

### 目標
先修已知資料一致性問題，再補 API 穩定性，最後做 web UI 改善。這一階段不做大型重構，不改 route contract。

### P1-A ✅ COMPLETED — Mobile Responsive Navigation
**改動：**
- `web/src/components/Header.tsx`：body scroll lock、Escape 鍵關閉、backdrop click 關閉、route click 關閉、mobile nav header、Cart/Wishlist badge、Admin/Ops 分區
- `web/src/components/Header.module.css`：breakpoint `768px`、full-screen overlay、實體 backdrop、mobile search 固定到 header 下方、修 iPhone 11 overflow
- `web/src/components/Footer.tsx`：修 duplicate React key warning，令 smoke console errors 清零
- `scripts/mobile-nav-contract.test.mjs`：contract test

**驗收：**
- `node --test scripts/mobile-nav-contract.test.mjs`：pass
- `npm run lint`：pass，7 個舊有 API console warnings
- `npm run check`：pass
- Playwright iPhone 11 smoke：pass（menu opens、full-screen、navigation、scroll lock、Escape close、console 0 errors）
- Screenshots：`/tmp/cloth-mobile-menu.png`、`/tmp/cloth-desktop-header.png`

### P1-B ✅ COMPLETED — market persistence
**改動：**
- 加 regression test (`scripts/product-market-persistence.test.mjs`)
- 修 `api/src/routes/products.ts`：create/update 保存 market，接受 UK/HK/CN/ALL，非法值 fallback ALL

**驗收：**
- persistence test + mobile-nav-contract test + sqlite-store test + lint + check 全部 pass

### P1-C ✅ COMPLETED — Input validation + structured error handling
**改動：**
- `serverError`：只回安全錯誤訊息，唔爆 stack trace
- `errorHandler` middleware：JSON parse error 回 400 structured JSON
- 全域 `errorHandler` 已接入 Express，未捕獲錯誤不再回 HTML / stack trace
- 現有 400 inline responses 保持原有 response shape，避免破壞前端或 smoke test

**驗收：**
- `npm run lint`：pass，0 errors，7 個舊有 console warnings

### P1-D ✅ COMPLETED — API smoke contracts / filtering readiness
**改動：**
- 新增 `scripts/api-smoke.test.mjs`，單 server 跑 26 個 smoke cases
- 覆蓋 products / orders / finance / inventory / support 核心 route
- products smoke 覆蓋：GET list、POST create with market、required 400、`market=UK` filter、PUT update、DELETE soft-delete
- 修正 smoke test 對 response shape / pagination 的錯誤假設，不改 route contract
- 若 filtering / pagination 有進一步產品需求，拆入 Phase 2，不在 P1-D 展開

**驗收：**
```bash
cd /Users/rubykan/Documents/CLOTH
node --test scripts/api-smoke.test.mjs
node --test scripts/api-validation-errors.test.mjs
node --test scripts/product-market-persistence.test.mjs
node --test scripts/mobile-nav-contract.test.mjs
node --import tsx --test api/src/db/sqlite-store.test.ts
npm run lint
npm run check
```

**結果：**
- `scripts/api-smoke.test.mjs`：26 passed
- `api-validation-errors`：2 passed
- `product-market-persistence`：1 passed
- `mobile-nav-contract`：1 passed
- `sqlite-store`：3 passed
- `npm run lint`：pass，0 errors，7 個既有 console warnings
- `npm run check`：pass
- PR #7 merged into `cursor/github-actions-workflows` at `ff1d23b`（2026-05-25）

## Phase 2 ⏳ P2-A REVIEW — Filtering / Pagination

### Automation controller note
- Shared controller: `/Users/rubykan/Documents/team/automation/`
- CLOTH `check` lane includes `npm run check`, `npm run lint`, API smoke, validation, market persistence, and products filtering pagination tests
- CLOTH production deploy target path selected: `/opt/cloth`
- CLOTH deploy service manager selected: systemd
- CLOTH `deploy` lane includes `infra/cloth_deploy.sh`, `infra/cloth_rollback.sh`, nginx reverse proxy template, and systemd service template
- Secret-scan false-positive for env-name references has been fixed in shared controller commit `45a81fc`
- AI Try-On boundary doc committed in CLOTH: `4480639 docs: define CLOTH ai try-on boundary`
- CLOTH deploy adapter committed: `d5b6d1f infra: add CLOTH systemd deploy adapter`
- Latest automation report on 2026-05-26 02:43 UTC: CLOTH deploy dry-run PASS/open; real deploy still needs VPS/nginx/systemd validation.

### Contract
- 詳細契約已寫入：`/Users/rubykan/Documents/CLOTH/docs/PHASE_2_CONTRACT.md`
- 第一刀只做 `GET /api/products` filtering / pagination readiness
- 不改 UI、不改 auth、不改 finance / inventory / support route contract
- 保留現有 response wrapper：`{ success: true, data: { data, total, page, limit, totalPages } }`
- 禁止大型 query builder / specification pattern；用現有 store/db pattern 做簡潔實作

### P2-A opened
- PR： https://github.com/uugiftcard-sudo/ai-luxury-resale-os/pull/9
- Branch：`codex/cloth-phase2-products-filter`
- 2026-05-27 update：local ahead 2 resolved by pushing `4480639..04feb94`; branch is now 0 ahead / 0 behind. Live `gh pr status` shows PR #9 checks pending after push.
- Query params：`market/status/brand/category/condition/minPrice/maxPrice/search/page/limit/sort`
- Validation：invalid enum / numeric / range → 400 JSON
- Tests：`scripts/products-filter-pagination.test.mjs`
- Scope：只改 `GET /api/products` + contract enum correction；不改 UI/auth/finance/inventory/support

## API 路由一覽
| Route | 檔案 |
|-------|------|
| Products | `api/src/routes/products.ts` |
| Orders | `api/src/routes/orders.ts` |
| Live | `api/src/routes/live.ts` |
| Finance | `api/src/routes/finance.ts` |
| Inventory | `api/src/routes/inventory.ts` |
| Support | `api/src/routes/support.ts` |

## Web UI Components
| Component | 檔案 |
|-----------|------|
| Header | `web/src/components/Header.tsx` |
| Footer | `web/src/components/Footer.tsx` |
| Header CSS | `web/src/components/Header.module.css` |

## Scripts
| Script | 用途 |
|--------|------|
| `scripts/mobile-nav-contract.test.mjs` | P1-A contract test |
| `scripts/product-market-persistence.test.mjs` | P1-B regression test |
| `scripts/api-validation-errors.test.mjs` | P1-C validation/error handling regression test |
| `scripts/api-smoke.test.mjs` | P1-D API smoke contracts |

## Dev Server
- URL：http://127.0.0.1:3002/
- API：port 3002

## Notes
- Phase 1 已完成。下一步可做 Phase 2 filtering / pagination readiness，或轉 BuyerOS（仍 blocked：Supabase API Keys + VPS SSH）。
