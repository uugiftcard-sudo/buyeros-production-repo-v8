# Automation Report

- Generated: 2026-05-27 19:24 UTC
- Dry run: no

| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |
|---|---:|---:|---:|---:|---|
| BuyerOS | PASS | yes | no | blocked | dirty working tree blocks deploy |

## BuyerOS

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/buyeros-m1-ui-smoke
upstream: origin/codex/buyeros-m1-ui-smoke
ahead: 0; behind: 0
github pr status: unavailable
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
====================== 236 passed, 324 warnings in 13.87s ======================
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
 ✓ Compiled successfully in 2.1s
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

[2m[WebServer] [22m(node:49733) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22m(node:49734) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)

Running 2 tests using 2 workers

  -  1 [chromium] › tests/buyeros-live-proxy.smoke.spec.ts:6:7 › BuyerOS live backend proxy smoke › main controls reach the real local backend through the Next.js proxy
(node:49751) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:49751) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22m(node:49758) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22m[next-auth][warn][NEXTAUTH_URL]
[2m[WebServer] [22mhttps://next-auth.js.org/warnings#nextauth_url
[2m[WebServer] [22m[next-auth][warn][NO_SECRET]
[2m[WebServer] [22mhttps://next-auth.js.org/warnings#no_secret
  ✓  2 [chromium] › tests/buyeros-ui.smoke.spec.ts:3:5 › BuyerOS mission control can plan, run one step, and show memory UI (19.2s)

  1 skipped
  1 passed (25.7s)
```

- PASS `live backend-proxy UI smoke`: `bash infra/smoke_ui_live_proxy.sh`

```text
Starting BuyerOS backend on 127.0.0.1:8010
Starting BuyerOS frontend on 127.0.0.1:3010
Running live backend-proxy UI smoke

> buyeros-admin-ui@0.1.0 ui:smoke
> playwright test tests/buyeros-live-proxy.smoke.spec.ts


Running 1 test using 1 worker

(node:49896) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:49896) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ✓  1 [chromium] › tests/buyeros-live-proxy.smoke.spec.ts:6:7 › BuyerOS live backend proxy smoke › main controls reach the real local backend through the Next.js proxy (15.8s)

  1 passed (17.0s)
BuyerOS live backend-proxy UI smoke OK
```

- PASS `http runtime smoke`: `python3 with_server.py --cwd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend --command 'npm run dev -- --hostname 127.0.0.1 --port 3000' --ready-url http://127.0.0.1:3000 -- python3 smoke_http.py buyeros --base-url http://127.0.0.1:3000`

```text
PASS dashboard shell: http://127.0.0.1:3000/
PASS ops anchor: http://127.0.0.1:3000/#ops
```

- Blockers: dirty working tree blocks deploy
