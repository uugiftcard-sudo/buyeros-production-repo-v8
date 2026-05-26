# Automation Report

- Generated: 2026-05-25 23:43 UTC
- Dry run: no

| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |
|---|---:|---:|---:|---:|---|
| BuyerOS | FAIL | yes | no | blocked | dirty working tree blocks deploy |
| XAU | PASS | no | no | open | - |
| CLOTH | FAIL | yes | yes | blocked | dirty working tree blocks deploy; secret-like pattern found in git diff |

## BuyerOS

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/buyeros-redis-orchestration-clean
upstream: origin/codex/buyeros-redis-orchestration-clean
ahead: 0; behind: 0
github pr status: gh not installed
```

- PASS `backend pytest`: `/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short`

```text
supervisor_buyer_routing PASSED [ 90%]
backend/tests/test_telegram_webhook.py::test_telegram_webhook_secret_when_configured PASSED [ 90%]
backend/tests/test_telegram_webhook.py::test_telegram_webhook_malformed_json_returns_400 PASSED [ 91%]
backend/tests/test_telegram_webhook.py::test_telegram_webhook_no_message_returns_ok_empty PASSED [ 91%]
backend/tests/test_telegram_webhook.py::test_telegram_webhook_no_text_returns_ok PASSED [ 91%]
backend/tests/test_telegram_webhook.py::test_telegram_webhook_edited_message_handled PASSED [ 92%]
backend/tests/test_telegram_webhook.py::test_telegram_refund_then_recall_sends_persisted_reply PASSED [ 92%]
backend/tests/test_three_line_modules.py::test_reporting_service_creates_history_and_csv PASSED [ 93%]
backend/tests/test_three_line_modules.py::test_promo_service_campaign_event_metrics PASSED [ 93%]
backend/tests/test_three_line_modules.py::test_task_board_service_lifecycle PASSED [ 94%]
backend/tests/test_three_line_modules.py::test_task_board_accepts_three_workspace_lanes_and_legacy_aliases PASSED [ 94%]
backend/tests/test_three_line_modules.py::test_project_registry_returns_three_canonical_projects_when_old_alias_projects_exist PASSED [ 94%]
backend/tests/test_three_line_modules.py::test_three_system_api_endpoints PASSED [ 95%]
backend/tests/test_three_line_modules.py::test_three_system_api_validates_payload PASSED [ 95%]
backend/tests/test_three_line_modules.py::test_three_systems_smoke_script_exists_and_is_executable PASSED [ 96%]
backend/tests/test_three_line_modules.py::test_primary_smoke_script_runs_three_systems_by_default PASSED [ 96%]
backend/tests/test_three_line_modules.py::test_legacy_three_systems_smoke_script_wraps_three_systems PASSED [ 97%]
backend/tests/test_three_line_modules.py::test_deploy_and_smoke_script_exists_and_uses_safe_steps PASSED [ 97%]
backend/tests/test_three_line_modules.py::test_24h_smoke_script_exists_and_runs_primary_smoke_loop PASSED [ 97%]
backend/tests/test_three_line_modules.py::test_smoke_full_script_exists PASSED [ 98%]
backend/tests/test_three_line_modules.py::test_restore_test_script_exits_nonzero_on_failure_branches PASSED [ 98%]
backend/tests/test_three_line_modules.py::test_run_ops_drill_syncs_summaries_even_when_failover_fails PASSED [ 99%]
backend/tests/test_three_line_modules.py::test_staging_rollback_drill_script_exists_and_never_targets_primary_rollback PASSED [ 99%]
backend/tests/test_three_line_modules.py::test_rollback_vps_supports_release_layout_current_symlink PASSED [100%]

=============================== warnings summary ===============================
backend/tests/test_business_automation.py: 2 warnings
backend/tests/test_context_api.py: 5 warnings
backend/tests/test_context_api_full.py: 19 warnings
backend/tests/test_integration_routing.py: 2 warnings
backend/tests/test_orchestration.py: 4 warnings
backend/tests/test_p0_command_center.py: 4 warnings
backend/tests/test_security.py: 10 warnings
backend/tests/test_telegram_webhook.py: 6 warnings
backend/tests/test_three_line_modules.py: 2 warnings
  /Users/rubykan/Downloads/buyeros-production-repo-v8/backend/app/workflows/main.py:530: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

backend/tests/test_business_automation.py: 6 warnings
backend/tests/test_context_api.py: 15 warnings
backend/tests/test_context_api_full.py: 57 warnings
backend/tests/test_integration_routing.py: 6 warnings
backend/tests/test_orchestration.py: 12 warnings
backend/tests/test_p0_command_center.py: 12 warnings
backend/tests/test_security.py: 30 warnings
backend/tests/test_telegram_webhook.py: 18 warnings
backend/tests/test_three_line_modules.py: 6 warnings
  /Users/rubykan/miniconda3/lib/python3.13/site-packages/fastapi/applications.py:4580: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)

backend/tests/test_business_automation.py: 2 warnings
backend/tests/test_context_api.py: 5 warnings
backend/tests/test_context_api_full.py: 19 warnings
backend/tests/test_integration_routing.py: 2 warnings
backend/tests/test_orchestration.py: 4 warnings
backend/tests/test_p0_command_center.py: 4 warnings
backend/tests/test_security.py: 10 warnings
backend/tests/test_telegram_webhook.py: 6 warnings
backend/tests/test_three_line_modules.py: 2 warnings
  /Users/rubykan/Downloads/buyeros-production-repo-v8/backend/app/workflows/main.py:534: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

backend/tests/test_business_automation.py: 2 warnings
backend/tests/test_context_api.py: 5 warnings
backend/tests/test_context_api_full.py: 19 warnings
backend/tests/test_integration_routing.py: 2 warnings
backend/tests/test_orchestration.py: 4 warnings
backend/tests/test_p0_command_center.py: 4 warnings
backend/tests/test_security.py: 10 warnings
backend/tests/test_telegram_webhook.py: 6 warnings
backend/tests/test_three_line_modules.py: 2 warnings
  /Users/rubykan/Downloads/buyeros-production-repo-v8/backend/app/workflows/main.py:900: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 234 passed, 324 warnings in 16.52s ======================
```

- PASS `frontend lint`: `npm run lint`

```text
> buyeros-admin-ui@0.1.0 lint
> tsc --noEmit
```

- PASS `frontend build`: `npm run build`

```text
> buyeros-admin-ui@0.1.0 build
> next build

   ▲ Next.js 15.5.18

   Creating an optimized production build ...
 ✓ Compiled successfully in 2.4s
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/6) ...
   Generating static pages (1/6) 
   Generating static pages (2/6) 
   Generating static pages (4/6) 
 ✓ Generating static pages (6/6)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                 Size  First Load JS
┌ ○ /                                    12.1 kB         115 kB
├ ○ /_not-found                            990 B         103 kB
├ ƒ /api/auth/[...nextauth]                130 B         103 kB
├ ƒ /api/buyeros/[...path]                 130 B         103 kB
├ ○ /auth/error                            679 B         103 kB
└ ○ /auth/signin                         1.27 kB         113 kB
+ First Load JS shared by all             102 kB
  ├ chunks/255-4f84124391a7dac4.js       46.2 kB
  ├ chunks/4bd1b696-c023c6e3521b1417.js  54.2 kB
  └ other shared chunks (total)          1.92 kB


○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```

- PASS `ui smoke`: `npm run ui:smoke`

```text
> buyeros-admin-ui@0.1.0 ui:smoke
> playwright test

[WebServer] (node:63904) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[WebServer] (Use `node --trace-warnings ...` to show where the warning was created)
[WebServer] (node:63906) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[WebServer] (Use `node --trace-warnings ...` to show where the warning was created)

Running 1 test using 1 worker

(node:63934) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:63934) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[WebServer] (node:63965) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[WebServer] (Use `node --trace-warnings ...` to show where the warning was created)
[WebServer] [next-auth][warn][NEXTAUTH_URL] 
[WebServer] https://next-auth.js.org/warnings#nextauth_url
[WebServer] [next-auth][warn][NO_SECRET] 
[WebServer] https://next-auth.js.org/warnings#no_secret
  ✓  1 [chromium] › tests/buyeros-ui.smoke.spec.ts:3:5 › BuyerOS mission control can plan, run one step, and show memory UI (11.2s)

  1 passed (19.0s)
```

- PASS `http runtime smoke`: `python3 with_server.py --cwd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend --command 'npm run dev -- --hostname 127.0.0.1 --port 3000' --ready-url http://127.0.0.1:3000 -- python3 smoke_http.py buyeros --base-url http://127.0.0.1:3000`

```text
PASS dashboard shell: http://127.0.0.1:3000/
PASS ops anchor: http://127.0.0.1:3000/#ops
```

- Blockers: dirty working tree blocks deploy

## XAU

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/xau-dashboard-live-ui
upstream: origin/codex/xau-dashboard-live-ui
ahead: 0; behind: 0
github pr status: gh not installed
```

- PASS `server tests`: `npm run test:server`

```text
> xau-ai-platform@1.0.0 test:server
> cd server && npm test


> xau-server@1.0.0 test
> NODE_ENV=test node --test ../tests/server.test.js

[priceService] Created — call startPolling() to begin fetching
▶ GET /health
  ✔ 返回 200 和 status=ok (44.774475ms)
✔ GET /health (594.176511ms)
[priceService] All real sources unavailable — falling back to Mock
▶ GET /api/prices/quote
  ✔ 返回报价 (4.575499ms)
  ✔ 第二次请求返回缓存 (3.774421ms)
✔ GET /api/prices/quote (8.645745ms)
▶ GET /api/prices/history
  ✔ 返回历史数据 (2.961058ms)
✔ GET /api/prices/history (3.305104ms)
▶ GET /api/ai/script/fallback
  ✔ 返回三种讲稿 (2.820229ms)
✔ GET /api/ai/script/fallback (3.151429ms)
▶ POST /api/ai/script
  ✔ 正常请求返回 fallback 讲稿 (16.529918ms)
  ✔ 缺少 biasType 返回 400 (3.196915ms)
  ✔ 非法 biasType 返回 400 (3.319455ms)
✔ POST /api/ai/script (23.53597ms)
▶ GET /api/state
  ✔ 返回全局 state (3.366373ms)
✔ GET /api/state (3.677978ms)
▶ POST /api/state
  ✔ 推送 state 返回 ok (3.839623ms)
✔ POST /api/state (4.068241ms)
▶ GET /api/news/latest
  ✔ 返回直播室和 App 可用的新聞提示 fallback (2.970218ms)
✔ GET /api/news/latest (3.144826ms)
▶ POST /api/tts
  ✔ 寫入 browser speech 並同步到 state (4.905591ms)
  ✔ 列出可用口播 provider (2.43094ms)
  ✔ ElevenLabs 缺少 voiceId 返回 400 (3.512723ms)
  ✔ ElevenLabs speak-to-file 缺少 voiceId 返回 400 (2.262029ms)
✔ POST /api/tts (13.579431ms)
▶ GET /api/clients/types
  ✔ 返回类型列表和题目 (1.931643ms)
✔ GET /api/clients/types (2.100643ms)
00:42:47 [info] [clients] 新客户测评完成: 0e47c825-f2d5-4b18-924f-bfae31413e6e -> 短线型
▶ POST /api/clients/quiz
  ✔ 完整作答返回类型 (8.087628ms)
  ✔ 部分作答返回 400 (2.889492ms)
✔ POST /api/clients/quiz (11.268955ms)
[signals] New up signal: sig_daefd9c3
▶ POST /api/signals
  ✔ 创建信号返回 201 (4.470597ms)
  ✔ 缺少 type 返回 400 (2.908723ms)
✔ POST /api/signals (8.100471ms)
▶ GET /api/signals
  ✔ 返回信号列表 (3.31339ms)
✔ GET /api/signals (3.920746ms)
▶ GET /api
  ✔ 返回 API 端点列表 (2.984634ms)
✔ GET /api (3.295053ms)
ℹ tests 22
ℹ suites 14
ℹ pass 22
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1142.804668
```

- PASS `analysis output tests`: `node --test tests/analysis-output.test.js`

```text
▶ calculateXAUAnalysis
  ✔ builds bullish XAUAnalysis with 上格 and confirm-before-push signal pool (5.174661ms)
  ✔ keeps high-news neutral setup in 等格 with signal pool paused (0.489753ms)
  ✔ builds bearish breakdown setup with 落格 and short-side levels (0.537344ms)
✔ calculateXAUAnalysis (8.268379ms)
▶ buildGridCards
  ✔ always returns 上格 / 等格 / 落格 with only the active grid highlighted (2.60713ms)
✔ buildGridCards (2.877673ms)
ℹ tests 4
ℹ suites 2
ℹ pass 4
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 159.789338
```

- PASS `http ui smoke`: `python3 with_server.py --cwd /Users/rubykan/Documents/XAU --command 'PORT=3002 npm run dev' --ready-url http://127.0.0.1:3002/health -- python3 smoke_http.py xau --base-url http://127.0.0.1:3002`

```text
PASS dashboard: http://127.0.0.1:3002/
PASS OBS scene: http://127.0.0.1:3002/stream/obs-scene.html
PASS server health: http://127.0.0.1:3002/health
```


## CLOTH

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/cloth-phase2-products-filter
upstream: origin/codex/cloth-phase2-products-filter
ahead: 0; behind: 0
github pr status: gh not installed
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
✓ 76 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.85 kB │ gzip:  0.52 kB
dist/assets/index-BpH2mxyu.css   79.90 kB │ gzip: 14.25 kB
dist/assets/index-DzEuN5To.js   314.83 kB │ gzip: 95.06 kB
✓ built in 1.96s
```

- PASS `lint`: `npm run lint`

```text
> cloth-marketplace@1.0.0 lint
> eslint api/src web/src --max-warnings=20
```

- PASS `api smoke`: `node --test scripts/api-smoke.test.mjs`

```text
> cloth-api@1.0.0 build
> tsc

✔ Products GET → 200 + array (756.007955ms)
✔ Products POST → 200 + created with market (22.047633ms)
✔ Products POST missing required → 400 (4.794496ms)
✔ Products market filter finds UK products (7.56783ms)
✔ Products PUT updates + persists (8.924306ms)
✔ Products DELETE → soft-deleted (status=已下架) (6.765228ms)
✔ Products status=ALL includes non-sale admin inventory products (10.343615ms)
✔ Orders GET → 200 + paginated (2.66355ms)
✔ Orders POST missing productId → 400 (3.450739ms)
✔ Orders PUT valid status → 200 (6.112617ms)
✔ Orders market filter isolates market-specific orders (14.926136ms)
✔ Finance GET → 200 + array (12.292883ms)
✔ Finance GET /stats → 200 + stats object (2.333039ms)
✔ Finance POST → 200 + created (2.725643ms)
✔ Finance POST invalid type → 400 (2.006629ms)
✔ Finance DELETE → removed (8.233711ms)
✔ Inventory GET → 200 + array (2.504513ms)
✔ Inventory GET /stats → 200 + stats (2.238959ms)
✔ Inventory POST → 200 + created (3.530796ms)
✔ Inventory POST missing sku/productName → 400 (2.300682ms)
✔ Inventory inbound → stock increases (5.727627ms)
✔ Inventory outbound → stock decreases (6.155357ms)
✔ Inventory outbound insufficient stock → 400 (4.634ms)
✔ Support tickets GET → 200 + array (1.90085ms)
✔ Support tickets POST → 200 + ticket with ticketNo (3.031874ms)
✔ Support tickets POST missing required → 400 (1.973631ms)
✔ Support FAQs GET → 200 + array (2.000291ms)
✔ Support ticket messages POST → 200 (4.226852ms)
ℹ tests 28
ℹ suites 0
ℹ pass 28
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3755.670909
```

- PASS `validation errors`: `node --test scripts/api-validation-errors.test.mjs`

```text
> cloth-api@1.0.0 build
> tsc


> cloth-api@1.0.0 build
> tsc

✔ POST routes return 400 JSON for missing required fields (3084.496327ms)

> cloth-api@1.0.0 build
> tsc

✔ malformed JSON returns structured JSON instead of HTML or stack trace (2920.463664ms)
✔ numeric fields reject invalid values instead of coercing to zero (3207.127642ms)
ℹ tests 3
ℹ suites 0
ℹ pass 3
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 9400.153528
```

- PASS `market persistence`: `node --test scripts/product-market-persistence.test.mjs`

```text
> cloth-api@1.0.0 build
> tsc

✔ POST /api/products persists market so market filtering can find the product (3466.086766ms)
ℹ tests 1
ℹ suites 0
ℹ pass 1
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3687.364454
```

- PASS `products filtering pagination`: `node --test scripts/products-filter-pagination.test.mjs`

```text
> cloth-api@1.0.0 build
> tsc

✔ products filtering supports market, category, price, search, sort, and pagination (733.401272ms)
✔ products filtering rejects invalid query params with 400 JSON (13.72517ms)
ℹ tests 2
ℹ suites 0
ℹ pass 2
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3908.560134
```

- PASS `mobile nav contract`: `node --test scripts/mobile-nav-contract.test.mjs`

```text
✔ mobile navigation implements the Phase 1 overlay contract (1.284699ms)
ℹ tests 1
ℹ suites 0
ℹ pass 1
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 153.830319
```

- PASS `http api/ui smoke`: `python3 with_server.py --cwd /Users/rubykan/Documents/CLOTH --command 'PORT=3001 npm run dev --workspace=api' --ready-url http://127.0.0.1:3001/api/health -- python3 smoke_http.py cloth --base-url http://127.0.0.1:3001`

```text
PASS API health: http://127.0.0.1:3001/api/health
PASS live readiness: http://127.0.0.1:3001/api/live/readiness
PASS products pagination: http://127.0.0.1:3001/api/products?limit=3
PASS support faqs: http://127.0.0.1:3001/api/support/faqs
```

- Secret scan hits: OPENAI_API_KEY
- Blockers: dirty working tree blocks deploy; secret-like pattern found in git diff
