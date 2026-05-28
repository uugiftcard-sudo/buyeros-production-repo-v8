# Automation Report

- Generated: 2026-05-28 07:52 UTC
- Dry run: no

| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |
|---|---:|---:|---:|---:|---|
| CLOTH | FAIL | no | no | blocked | - |

## CLOTH

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/cloth-admin-market-contract
upstream: origin/codex/cloth-admin-market-contract
ahead: 0; behind: 0
github pr status: unavailable
```

- PASS `type/build check`: `npm run check`

```text
> cloth-marketplace@1.0.0 check
> npm run build


> cloth-marketplace@1.0.0 build
> npm run build --workspace=api && npm run build --workspace=web


> cloth-api@1.0.0 build
> tsc


> cloth-web@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 77 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.85 kB │ gzip:  0.52 kB
dist/assets/index-BEiVVUG5.css   83.80 kB │ gzip: 14.84 kB
dist/assets/index-BxkHyllk.js   314.30 kB │ gzip: 93.68 kB
✓ built in 3.23s
```

- PASS `lint`: `npm run lint`

```text
> cloth-marketplace@1.0.0 lint
> eslint api/src web/src --max-warnings=20
```

- PASS `api smoke`: `node --test scripts/api-smoke.test.mjs`

```text
TAP version 13
# Subtest: Products GET → 200 + array
ok 1 - Products GET → 200 + array
  ---
  duration_ms: 45.831791
  type: 'test'
  ...
# Subtest: Products POST → 200 + created with market
ok 2 - Products POST → 200 + created with market
  ---
  duration_ms: 141.132387
  type: 'test'
  ...
# Subtest: Products POST missing required → 400
ok 3 - Products POST missing required → 400
  ---
  duration_ms: 10.55383
  type: 'test'
  ...
# Subtest: Products market filter finds UK products
ok 4 - Products market filter finds UK products
  ---
  duration_ms: 32.306513
  type: 'test'
  ...
# Subtest: Products PUT updates + persists
ok 5 - Products PUT updates + persists
  ---
  duration_ms: 29.429696
  type: 'test'
  ...
# Subtest: Products DELETE → soft-deleted (status=已下架)
ok 6 - Products DELETE → soft-deleted (status=已下架)
  ---
  duration_ms: 12.673833
  type: 'test'
  ...
# Subtest: Orders GET → 200 + paginated
ok 7 - Orders GET → 200 + paginated
  ---
  duration_ms: 5.557026
  type: 'test'
  ...
# Subtest: Orders POST missing productId → 400
ok 8 - Orders POST missing productId → 400
  ---
  duration_ms: 9.63616
  type: 'test'
  ...
# Subtest: Orders PUT valid status → 200
ok 9 - Orders PUT valid status → 200
  ---
  duration_ms: 8.556589
  type: 'test'
  ...
# Subtest: Finance GET → 200 + array
ok 10 - Finance GET → 200 + array
  ---
  duration_ms: 3.016283
  type: 'test'
  ...
# Subtest: Finance GET /stats → 200 + stats object
ok 11 - Finance GET /stats → 200 + stats object
  ---
  duration_ms: 2.863823
  type: 'test'
  ...
# Subtest: Finance POST → 200 + created
ok 12 - Finance POST → 200 + created
  ---
  duration_ms: 5.032923
  type: 'test'
  ...
# Subtest: Finance POST invalid type → 400
ok 13 - Finance POST invalid type → 400
  ---
  duration_ms: 4.820806
  type: 'test'
  ...
# Subtest: Finance DELETE → removed
ok 14 - Finance DELETE → removed
  ---
  duration_ms: 11.01279
  type: 'test'
  ...
# Subtest: Inventory GET → 200 + array
ok 15 - Inventory GET → 200 + array
  ---
  duration_ms: 5.405994
  type: 'test'
  ...
# Subtest: Inventory GET /stats → 200 + stats
ok 16 - Inventory GET /stats → 200 + stats
  ---
  duration_ms: 2.828351
  type: 'test'
  ...
# Subtest: Inventory POST → 200 + created
ok 17 - Inventory POST → 200 + created
  ---
  duration_ms: 30.140843
  type: 'test'
  ...
# Subtest: Inventory POST missing sku/productName → 400
ok 18 - Inventory POST missing sku/productName → 400
  ---
  duration_ms: 87.540606
  type: 'test'
  ...
# Subtest: Inventory inbound → stock increases
ok 19 - Inventory inbound → stock increases
  ---
  duration_ms: 31.069711
  type: 'test'
  ...
# Subtest: Inventory outbound → stock decreases
ok 20 - Inventory outbound → stock decreases
  ---
  duration_ms: 9.866323
  type: 'test'
  ...
# Subtest: Inventory outbound insufficient stock → 400
ok 21 - Inventory outbound insufficient stock → 400
  ---
  duration_ms: 12.811043
  type: 'test'
  ...
# Subtest: Support tickets GET → 200 + array
ok 22 - Support tickets GET → 200 + array
  ---
  duration_ms: 6.125531
  type: 'test'
  ...
# Subtest: Support tickets POST → 200 + ticket with ticketNo
ok 23 - Support tickets POST → 200 + ticket with ticketNo
  ---
  duration_ms: 7.79354
  type: 'test'
  ...
# Subtest: Support tickets POST missing required → 400
ok 24 - Support tickets POST missing required → 400
  ---
  duration_ms: 14.895176
  type: 'test'
  ...
# Subtest: Support FAQs GET → 200 + array
ok 25 - Support FAQs GET → 200 + array
  ---
  duration_ms: 4.302694
  type: 'test'
  ...
# Subtest: Support ticket messages POST → 200
ok 26 - Support ticket messages POST → 200
  ---
  duration_ms: 14.930499
  type: 'test'
  ...
1..26
# tests 26
# suites 0
# pass 26
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 988.387862
```

- PASS `validation errors`: `node --test scripts/api-validation-errors.test.mjs`

```text
TAP version 13
# Subtest: POST routes return 400 JSON for missing required fields
ok 1 - POST routes return 400 JSON for missing required fields
  ---
  duration_ms: 284.11006
  type: 'test'
  ...
# Subtest: malformed JSON returns structured JSON instead of HTML or stack trace
ok 2 - malformed JSON returns structured JSON instead of HTML or stack trace
  ---
  duration_ms: 66.177378
  type: 'test'
  ...
# Subtest: numeric fields reject invalid values instead of coercing to zero
ok 3 - numeric fields reject invalid values instead of coercing to zero
  ---
  duration_ms: 80.496691
  type: 'test'
  ...
1..3
# tests 3
# suites 0
# pass 3
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 731.64872
```

- FAIL `market persistence`: `node --test scripts/product-market-persistence.test.mjs`

```text
TAP version 13
# Subtest: POST /api/products persists market so market filtering can find the product
not ok 1 - POST /api/products persists market so market filtering can find the product
  ---
  duration_ms: 185.715324
  type: 'test'
  location: '/Users/rubykan/Documents/CLOTH/scripts/product-market-persistence.test.mjs:36:1'
  failureType: 'testCodeFailure'
  error: |-
    Expected values to be strictly equal:
    
    2 !== 1
    
  code: 'ERR_ASSERTION'
  name: 'AssertionError'
  expected: 1
  actual: 2
  operator: 'strictEqual'
  stack: |-
    TestContext.<anonymous> (file:///Users/rubykan/Documents/CLOTH/scripts/product-market-persistence.test.mjs:79:12)
    process.processTicksAndRejections (node:internal/process/task_queues:105:5)
    async Test.run (node:internal/test_runner/test:1054:7)
    async startSubtestAfterBootstrap (node:internal/test_runner/harness:296:3)
  ...
1..1
# tests 1
# suites 0
# pass 0
# fail 1
# cancelled 0
# skipped 0
# todo 0
# duration_ms 612.665524
```

- PASS `products filtering pagination`: `node --test scripts/products-filter-pagination.test.mjs`

```text
TAP version 13
# Subtest: products filtering supports market, category, price, search, sort, and pagination
ok 1 - products filtering supports market, category, price, search, sort, and pagination
  ---
  duration_ms: 120.181846
  type: 'test'
  ...
# Subtest: products filtering rejects invalid query params with 400 JSON
ok 2 - products filtering rejects invalid query params with 400 JSON
  ---
  duration_ms: 22.574659
  type: 'test'
  ...
1..2
# tests 2
# suites 0
# pass 2
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 523.819272
```

- PASS `mobile nav contract`: `node --test scripts/mobile-nav-contract.test.mjs`

```text
TAP version 13
# Subtest: mobile navigation implements the Phase 1 overlay contract
ok 1 - mobile navigation implements the Phase 1 overlay contract
  ---
  duration_ms: 2.479845
  type: 'test'
  ...
1..1
# tests 1
# suites 0
# pass 1
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 204.286889
```

- PASS `http api/ui smoke`: `python3 with_server.py --timeout 180 --cwd /Users/rubykan/Documents/CLOTH --command 'cd /Users/rubykan/Documents/CLOTH && PORT=3499 npm run dev --workspace=api' --ready-url http://127.0.0.1:3499/api/health -- python3 smoke_http.py cloth --base-url http://127.0.0.1:3499`

```text
PASS API health: http://127.0.0.1:3499/api/health
PASS live readiness: http://127.0.0.1:3499/api/live/readiness
PASS products pagination: http://127.0.0.1:3499/api/products?limit=3
PASS support faqs: http://127.0.0.1:3499/api/support/faqs
```
