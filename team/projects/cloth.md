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

## Phase 2 ✅ P2-A MERGED — Filtering / Pagination

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
- Branch：merged into `cursor/github-actions-workflows`
- 2026-05-27 update：PR #9 merged at `7256511`; local branch `cursor/github-actions-workflows` is 0 ahead / 0 behind.
- Query params：`market/status/brand/category/condition/minPrice/maxPrice/search/page/limit/sort`
- Validation：invalid enum / numeric / range → 400 JSON
- Tests：`scripts/products-filter-pagination.test.mjs`
- Scope：只改 `GET /api/products` + contract enum correction；不改 UI/auth/finance/inventory/support

## Functional completion project — Milestone 0 UI map

Last updated: 2026-05-27 19:55 UTC by Codex.

Source plan:
- `/Users/rubykan/Documents/team/automation/FUNCTION_COMPLETION_PROJECT.md`

Important correction:
- CLOTH is not function-complete just because API smoke and Phase 2 filtering pass.
- Browser route-load smoke has now been run for the primary desktop routes, but deeper interaction smoke is still required before final completion.

Latest fix:
- Branch: `codex/cloth-admin-market-contract`
- Commit: `6166ab6 fix: align admin product market contract`
- Draft PR: https://github.com/uugiftcard-sudo/ai-luxury-resale-os/pull/11
- Fixed `/admin` route browser smoke failure caused by `productApi.list(market, { limit: 100 })` exceeding the API `limit <= 50` validation.
- Fixed frontend product create/update client so the selected `market` is included in the request body.

Latest validation:
- `node --test scripts/admin-product-contract.test.mjs`: 2 passed
- `npm run check`: pass
- `npm run lint`: pass, 7 existing console warnings
- Browser route smoke at `http://127.0.0.1:5173`: 10/10 routes pass, 0 console errors, no horizontal overflow
- `node --test scripts/products-filter-pagination.test.mjs`: 2 passed
- `node --test scripts/product-market-persistence.test.mjs`: 1 passed
- `node --test scripts/api-smoke.test.mjs`: 26 passed when run standalone

Frontend route source:
- `/Users/rubykan/Documents/CLOTH/web/src/App.tsx`

API client sources:
- `/Users/rubykan/Documents/CLOTH/web/src/api/client.ts`
- `/Users/rubykan/Documents/CLOTH/web/src/api/finance.ts`
- `/Users/rubykan/Documents/CLOTH/web/src/api/support.ts`
- `/Users/rubykan/Documents/CLOTH/web/src/api/inventory.ts`

### CLOTH route map

The same core pages exist for UK default, HK, and CN market prefixes:

| Market | Home | Products | Detail | Cart | Orders | Admin | Support | Inventory | Warehouse admin | Finance | Wishlist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| UK | `/` | `/products` | `/products/:id` | `/cart` | `/orders` | `/admin` | `/support` | `/inventory` | `/admin/warehouse` | `/finance` | `/wishlist` |
| HK | `/hk` | `/hk/products` | `/hk/products/:id` | `/hk/cart` | `/hk/orders` | `/hk/admin` | `/hk/support` | `/hk/inventory` | `/hk/admin/warehouse` | `/hk/finance` | `/hk/wishlist` |
| CN | `/cn` | `/cn/products` | `/cn/products/:id` | `/cn/cart` | `/cn/orders` | `/cn/admin` | `/cn/support` | `/cn/inventory` | `/cn/admin/warehouse` | `/cn/finance` | `/cn/wishlist` |

### CLOTH workflow map

| Workflow | Route(s) | Data dependency | Current evidence | Status | Gap / next action |
|---|---|---|---|---|---|
| Home / market landing | `/`, `/hk`, `/cn` | `productApi.list`, `brandApi.list`, `categoryApi.list` | Route exists in `App.tsx`; home pages link to products by category/brand | PASS-CODE | Needs browser smoke for visible market copy and CTA links |
| Browse products | `/products`, `/hk/products`, `/cn/products` | `/api/products`, `/api/brands`, `/api/categories` | `products-filter-pagination.test.mjs` covers filtering/pagination API; ProductList controls exist | PASS-PARTIAL | Needs UI smoke for filter buttons, clear filter, next/prev pagination |
| Product detail | `*/products/:id` | `/api/products/:id`; cart/wishlist local state | ProductDetail has image selector, buy modal, add-to-cart button | PASS-CODE | Needs browser smoke for modal submit, add-to-cart feedback, sold-out disabled state |
| Cart | `*/cart` | localStorage cart + `orderApi.create` on checkout | Cart page has remove and checkout controls | PASS-CODE | Needs browser smoke for add/remove/update/checkout and order creation |
| Wishlist | `*/wishlist` | localStorage wishlist + product list API | ProductCard heart and Wishlist remove controls exist | PASS-CODE | Needs browser smoke for add/remove/list persistence |
| Orders | `*/orders` | `/api/orders` | API smoke covers order list/update; Orders page has status filters | PASS-PARTIAL | Needs UI smoke for status filter and product detail link |
| Admin products/orders | `*/admin` | `productApi`, `orderApi` | Admin route-load browser smoke passes after `limit=50` fix; add/edit/delete product form and order status select exist | PASS-PARTIAL | Needs deeper interaction smoke for add/edit/delete and order status updates |
| Finance | `*/finance` | `/api/finance`, `/api/finance/stats` | API smoke + numeric validation tests cover backend; Finance page has create/edit/delete/date filters | PASS-PARTIAL | Needs UI smoke for create/edit/delete/error feedback |
| Inventory | `*/inventory` | **web uses `mockStorage`, not `/api/inventory`** | API smoke covers backend; Inventory UI has inbound/outbound/add tabs | BLOCKED-PARTIAL | Wire web Inventory API to backend or explicitly mark as local demo |
| Warehouse admin | `*/admin/warehouse` | **web uses `mockStorage`, sessionStorage auth** | Route exists; login, list/add/inbound/outbound tabs exist | BLOCKED-PARTIAL | Needs browser smoke and decision: demo-only local storage vs backend inventory |
| Support | `*/support` | **web uses `mockStorage`, not `/api/support`** | API smoke covers backend; Support UI has list/new/FAQ tabs | BLOCKED-PARTIAL | Wire web support API to backend or explicitly mark as local demo |
| Mobile nav | all markets | React Router links + local cart/wishlist counts | `mobile-nav-contract.test.mjs` covers overlay contract | PASS-PARTIAL | Needs browser smoke for iPhone width, Escape close, route click, scroll lock |

### CLOTH button/control inventory

Source: read-only code evidence from `web/src/pages/*.tsx` and `web/src/api/*.ts`.
Key finding: **Inventory** (`web/src/api/inventory.ts`) and **Support** (`web/src/api/support.ts`) frontends use `mockStorage` (localStorage) — not real backend API. AdminWarehouse also uses `InventoryContext` → `mockStorage`. These pages are local demos, not API-backed.

#### UK / CN / HK shared control inventory

|| Page | Control | Text / Label | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|---|
| ProductList | Filter toggle button | "篩選" / "Filter" | Sets `filtersOpen` state, shows/hides filter panel | — | No API call; UI-only | PASS-CODE |
| ProductList | Brand dropdown | select | Sets `searchParams` brand, triggers re-render | — | No API call; URL-driven | PASS-CODE |
| ProductList | Category dropdown | select | Sets `searchParams` category | — | No API call; URL-driven | PASS-CODE |
| ProductList | Condition dropdown | select | Sets `searchParams` condition | — | No API call; URL-driven | PASS-CODE |
| ProductList | Clear filter button | "清除全部篩選" / "Clear All" | Clears all searchParams | — | No API call | PASS-CODE |
| ProductList | Prev page button | "上一页" / "← Prev" | Decrements page | `productApi.list()` | No loading/error state on button itself | PASS-CODE |
| ProductList | Next page button | "下一页" / "Next →" | Increments page | `productApi.list()` | No loading/error state on button itself | PASS-CODE |
| ProductList | ProductCard add to cart | heart icon | Calls `useCart().addItem()` | `useCart` localStorage | Toast feedback | PASS-CODE |
| ProductList | ProductCard add to wishlist | heart icon (filled) | Calls `useWishlist` localStorage toggle | localStorage | Visual toggle | PASS-CODE |
| ProductDetail | Add to cart | "加入購物車" / "Add to Cart" | `useCart().addItem()` + `showToast()` | `useCart` localStorage | Toast confirmation | PASS-CODE |
| ProductDetail | Buy now | "立即結算" / "Buy Now" | `useCart().addItem()` + `navigate('/cart')` | `useCart` localStorage | Toast + navigate | PASS-CODE |
| ProductDetail | Image thumbnail | img | Sets selected image index | — | Visual only | PASS-CODE |
| ProductDetail | Size selector | button | Sets selected size | — | Visual highlight | PASS-CODE |
| ProductDetail | Order form submit | "提交結算" | `orderApi.create()` | `/api/orders` | Success/error toast | PASS-CODE |
| Cart | Remove item | "×" | `useCart().removeItem()` | `useCart` localStorage | Immediate DOM removal | PASS-CODE |
| Cart | Checkout form | name/phone/address inputs | Controlled form state | — | Validation messages | PASS-CODE |
| Cart | Checkout submit | "結算" / "Checkout" | `orderApi.create()` → clear cart | `/api/orders` | Success navigate + toast | PASS-CODE |
| Wishlist | Remove from wishlist | "×" | `useWishlist` localStorage toggle | localStorage | Immediate DOM removal | PASS-CODE |
| Wishlist | Move to cart | "加入購物車" | `useCart().addItem()` | `useCart` localStorage | Toast feedback | PASS-CODE |
| Orders | Status filter tab | "全部"/"待付款"/etc. | Sets `filterStatus`, re-fetches | `orderApi.list()` | Loading spinner | PASS-PARTIAL |
| Orders | Order detail link | order item | `navigate()` to order detail | — | Navigation | PASS-CODE |
| Admin | Tab: products | "商品管理" / "Products" | Sets `activeTab` | — | UI-only | PASS-CODE |
| Admin | Tab: orders | "訂單管理" / "Orders" | Sets `activeTab` | — | UI-only | PASS-CODE |
| Admin | Add product button | "新增商品" / "Add Product" | Opens modal, sets `formOpen` | — | Modal opens | PASS-CODE |
| Admin | Edit product | edit icon | Opens modal with product data | — | Modal opens | PASS-CODE |
| Admin | Delete product | delete icon | `handleDelete(id)` | `productApi.delete()` | Confirm dialog expected but not visible in code | FAIL-AMBIGUOUS |
| Admin | Product form submit | "保存" / "Submit" | `handleSubmit()` → `productApi.create/update()` | `/api/products` | Success/error toast | PASS-CODE |
| Admin | Order status select | dropdown | `handleOrderStatus(orderId, status)` | `orderApi.updateStatus()` | Visual feedback | PASS-CODE |
| Finance | Tab: list/new/stats | — | Sets `activeTab` | — | UI-only | PASS-CODE |
| Finance | Date filter inputs | date inputs | Sets `filterDateFrom/to` | — | No API call on change | PASS-CODE |
| Finance | Clear date filter | "清除" | Clears date filters | — | UI-only | PASS-CODE |
| Finance | Edit record | edit button | `openEdit(r)` | — | Opens modal | PASS-CODE |
| Finance | Delete record | delete button | `handleDelete(id)` | `financeApi.delete()` | Success toast | PASS-CODE |
| Finance | Quick add income | income button | `openAdd('收入')` | — | Opens modal | PASS-CODE |
| Finance | Quick add expense | expense button | `openAdd('支出')` | — | Opens modal | PASS-CODE |
| Finance | Record form submit | "保存" / "Submit" | `handleSubmit()` → `financeApi.create/update()` | `/api/finance` | Success/error toast | PASS-CODE |
| Finance | Income/expense toggle | radio buttons | Sets `form.type` | — | UI-only | PASS-CODE |
| Inventory | Tab: list/add/inbound/outbound | — | Sets `tab` | — | UI-only | PASS-CODE |
| Inventory | Search input | search | Filters `items` locally | **mockStorage (localStorage)** | No API call | BLOCKED-DEMO |
| Inventory | Add form submit | submit | `handleSubmit()` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| Inventory | Inbound form submit | "確認入庫" | calls `inventoryApi.inbound()` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| Inventory | Outbound form submit | "確認出庫" | calls `inventoryApi.outbound()` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| AdminWarehouse | Login form | password input + submit | `handleLogin()` | — | Error message if wrong | PASS-PARTIAL |
| AdminWarehouse | Logout button | "登出" | Clears `sessionStorage`, sets `authenticated` | — | Immediate | PASS-CODE |
| AdminWarehouse | Tabs: items/add/inbound/outbound/transactions | — | Sets `activeTab` | — | UI-only | PASS-CODE |
| AdminWarehouse | Edit item | edit button | Opens add tab with item data | **mockStorage** | Modal form | BLOCKED-DEMO |
| AdminWarehouse | Item form submit | "新增商品"/"保存更改" | `createItem`/`updateItem` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| AdminWarehouse | Inbound form submit | "確認入庫" | `inbound()` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| AdminWarehouse | Outbound form submit | "確認出庫" | `outbound()` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| Support | Tab: list/new/FAQ | — | Sets `activeTab` | — | UI-only | PASS-CODE |
| Support | FAQ accordion | question | Toggles `open` state | — | UI accordion | PASS-CODE |
| Support | Order search | input + button | `handleOrderSearch()` | **mockStorage** | Result display | BLOCKED-DEMO |
| Support | New ticket form submit | submit | `handleSubmit()` → `supportApi.create()` | **mockStorage** | Toast (mock) | BLOCKED-DEMO |
| Support | Ticket expand | ticket header click | Toggles `open` | — | UI-only | PASS-CODE |
| Header | Mobile nav hamburger | menu icon | Toggles mobile overlay | — | Full-screen overlay | PASS-PARTIAL |
| Header | Cart icon | cart icon | Navigate to `/cart` | — | Navigation | PASS-CODE |
| Header | Wishlist icon | heart icon | Navigate to `/wishlist` | — | Navigation | PASS-CODE |
| Header | Market switch | market dropdown | Sets `market` in `useMarket` context | — | URL changes to `/hk/...` | PASS-PARTIAL |

### CLOTH workflow map — updated 2026-05-27

|| Workflow | Route(s) | Data dependency | Code evidence | Status | Gap |
|---|---|---|---|---|---|---|
| Home / market landing | `/`, `/hk`, `/cn` | `productApi.list`, `brandApi.list`, `categoryApi.list` | Routes exist; UKHome/HKHome/Home components exist | PASS-CODE | Browser smoke: visible market copy and CTA links |
| Browse products + filter | `/products`, `*/products` | `/api/products` + `/api/brands` + `/api/categories` | `ProductList` calls `productApi.list()` with market param; filter controls set searchParams | PASS-CODE | Browser smoke: filter toggle, brand/category/condition select, clear, prev/next pagination |
| Product detail | `*/products/:id` | `/api/products/:id` | `productApi.getById()`; add to cart → localStorage; buy now → order API | PASS-CODE | Browser smoke: image selector, size select, add to cart toast, buy modal submit |
| Cart | `*/cart` | localStorage + `/api/orders` | Remove from localStorage; checkout → `orderApi.create()` | PASS-CODE | Browser smoke: remove item, form validation, checkout success navigate |
| Wishlist | `*/wishlist` | localStorage + `/api/products` | `useWishlist` toggle; product cards from `productApi.list()` | PASS-CODE | Browser smoke: add/remove, move to cart |
| Orders | `*/orders` | `/api/orders` | `orderApi.list(market, status)`; status filter tabs | PASS-PARTIAL | Browser smoke: status filter tab click, order list load |
| Admin products | `*/admin` | `/api/products` + `/api/orders` | Route loads without console errors after `limit=50`; add/edit/delete product via `productApi`; order status via `orderApi` | PASS-PARTIAL | Needs interaction smoke for add/edit/delete and visible confirmation behavior |
| Admin orders | `*/admin` | `/api/orders` | Order status dropdown calls `orderApi.updateStatus()` | PASS-CODE | Browser smoke: status change → API call → visual update |
| Finance | `*/finance` | `/api/finance` + `/api/finance/stats` | `financeApi` CRUD; quick add income/expense; date filters | PASS-PARTIAL | Browser smoke: create/edit/delete with toast feedback |
| Inventory | `*/inventory` | **mockStorage (localStorage)** | `InventoryContext` → `inventoryApi` → `mockStorage` | **BLOCKED-DEMO** | Wire to `/api/inventory` or honestly label as local demo |
| Warehouse admin | `*/admin/warehouse` | **mockStorage (localStorage)** | `useInventory()` → `mockStorage`; password-gated | **BLOCKED-DEMO** | Wire to `/api/inventory` or honestly label as local demo |
| Support | `*/support` | **mockStorage (localStorage)** | `SupportContext` → `supportApi` → `mockStorage` | **BLOCKED-DEMO** | Wire to `/api/support` or honestly label as local demo |
| Mobile nav | all markets | React Router + localStorage counts | Header mobile hamburger; Playwright contract test exists | PASS-PARTIAL | Browser smoke: 390px width, Escape close, route click, scroll lock |

### Key blocker: CLOTH Inventory/Support/Warehouse are LOCAL DEMOS

**Confirmed on 2026-05-27 by code inspection:**

- `web/src/api/inventory.ts`: All methods call `inventoryStorage` (localStorage mock), not `/api/inventory`
- `web/src/api/support.ts`: All methods call `supportStorage` (localStorage mock), not `/api/support`
- `web/src/contexts/InventoryContext.tsx`: Calls `inventoryApi.list()` → mockStorage
- `web/src/contexts/SupportContext.tsx`: Calls `supportApi.list()` → mockStorage
- `web/src/pages/AdminWarehouse.tsx`: Uses `useInventory()` → mockStorage

**Backend smoke tests pass** (`/api/inventory`, `/api/support`) but the **frontend does NOT call them**. The backend exists and works; the frontend is disconnected.

**Two honest options:**
1. **Wire frontend to backend now** (M2 task): Replace `mockStorage` calls with real `fetch('/api/inventory')` and `fetch('/api/support')`
2. **Mark as local demo honestly**: Update docs to say Inventory/Support/Warehouse are browser-local demos that persist to localStorage

The backend API is production-ready; the frontend wiring is the gap.

### Subagent findings (2026-05-27) — additional issues

**CONFIRMED BUGS:**
1. `Inventory.tsx` InboundForm: `unitCost` field in state but **no visible input** — always `undefined` on submit
2. `AdminWarehouse` In/Out forms: `notes` field in `onSubmit` but **no visible textarea** — always empty string
3. `Orders.tsx` and `Admin.tsx`: API errors silently swallowed with `catch(() => {})` — **no user-visible error feedback**
4. `ProductDetail` modal: `×` button close works; backdrop click close works; no other issue
5. Promo poster download: `poster.html` download button shows browser alert instead of actual file download

**Dead / Non-Functional Controls:**
- `Inventory.tsx` InboundForm: `unitCost` always undefined (no visible input)
- `AdminWarehouse` In/Out: `notes` always empty string (no visible textarea)
- `poster.html` download: shows alert not actual download

**Notable UX issues:**
- Silent API failures in Orders and Admin pages
- Inventory/Support/Warehouse: localStorage demo, not real backend

### CLOTH M0-2 acceptance

All routes exist and are reachable. Key gaps:
- **Inventory / Support / Warehouse**: BLOCKED-DEMO — frontend uses localStorage, not backend API
- **Admin route load**: PASS — browser smoke passes after `limit=50` fix
- **Admin delete product**: PASS-PARTIAL — delete handler exists; interaction smoke still needs to verify confirm + feedback
- **Browser route smoke**: PASS 10/10 primary desktop routes; deeper control-level smoke still needed

### Immediate CLOTH next tasks

1. Decide: wire Inventory/Support/Warehouse frontend to real backend API, or honestly label as local demos
2. Add interaction smoke for product detail, cart checkout, wishlist, admin add/edit/delete, finance create/edit/delete, and mobile nav
3. Decide whether `window.confirm` is acceptable UX for Admin delete or replace it with visible modal confirmation
4. Update `cloth.md` after interaction evidence, not just route-load evidence

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
| `scripts/admin-product-contract.test.mjs` | Admin route/client contract regression |

## Dev Server
- URL：http://127.0.0.1:3002/
- API：port 3002

## Notes
- Phase 1 已完成。下一步可做 Phase 2 filtering / pagination readiness，或轉 BuyerOS（仍 blocked：Supabase API Keys + VPS SSH）。
