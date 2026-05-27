# BuyerOS Project Detail

## Current status
Last updated: 2026-05-27 19:30 UTC. BuyerOS Redis orchestration runtime PR #19 merged. BuyerOS M1 UI smoke PR #20 is open as draft, mergeable, and CI-green. Latest local automation dry-run reports PASS, dirty=no, secret diff=no, deploy gate=open. Local repo is on `codex/buyeros-m1-ui-smoke`, 0 ahead / 0 behind.

## Functional completion project — Milestone 0 inventory

Last updated: 2026-05-27 19:24 UTC by Codex.

Source plan:
- `/Users/rubykan/Documents/team/automation/FUNCTION_COMPLETION_PROJECT.md`

Important correction:
- BuyerOS is not function-complete just because repo hygiene is green or PR #19 merged.
- Current goal is real usable functionality: UI controls must be visible, clickable, and return clear output/fallback.

### BuyerOS UI map

Frontend source:
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/frontend/app/page.tsx`

Current routes/pages:

| Route / anchor | Status | Evidence | Notes / next action |
|---|---|---|---|
| `/` | PASS-PARTIAL | Next.js app has single dashboard page in `frontend/app/page.tsx` | Needs full browser review for all controls, not only mocked smoke |
| `#overview` | PASS-PARTIAL | Project workspace + AI team panels exist | Current Playwright smoke checks project card switch and provider row |
| `#agents` | PASS-PARTIAL | Static AI team role cards exist | Mostly informational; no action controls |
| `#dispatch` | PASS-SMOKE | Dispatch form, create plan, run next, run all controls exist | `codex/buyeros-m1-ui-smoke` smoke now covers create plan, run next, and `一鍵 Run All` |
| `#memory` | PASS-SMOKE | Timeline search and session context controls exist | Smoke now covers `查 Timeline` and `查看 Session Context` |
| `#tasks` | PASS-SMOKE | Task board controls exist: refresh, subtask, start, complete | Smoke now covers refresh, `分工`, `開始`, `完成` |
| `#projects` | PASS-SMOKE | Project switcher and workspace quick actions exist | Smoke now covers buyer_ai, commerce, and xau quick actions |
| `#ops` | PASS-SMOKE | Ops links: Health, Provider, Capabilities, Report History, Audit Log, Ops Status | Smoke now covers capabilities, report history, audit log, ops status |

### BuyerOS API / runtime map

Backend source:
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/backend/app/workflows/main.py`
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/backend/app/orchestration.py`

| API area | Endpoint(s) | Status | Evidence | Notes / next action |
|---|---|---|---|---|
| Projects | `GET /projects`, `POST /projects` | PASS-PARTIAL | Existing tests assert canonical `buyer_ai / commerce / xau` | UI smoke should confirm visible active project changes |
| Tasks | `GET /tasks`, `POST /tasks`, status/run/detail routes | PASS-PARTIAL | backend task board tests exist | UI task buttons need smoke |
| Dispatch plan | `POST /tasks/dispatch_plan` | PASS-PARTIAL | Playwright mock covers create plan | Need live backend smoke through proxy |
| Subtasks | `GET /tasks/{id}/subtasks`, `POST /subtasks/run`, `POST /subtasks/next`, `POST /run_all` | PASS-SMOKE | UI smoke verifies next + run_all request path | Live backend proxy smoke still desirable |
| Memory timeline | `POST /memory/timeline`, context session routes | PASS-SMOKE | UI smoke covers timeline + session context click | Live backend proxy smoke still desirable |
| Reports | `/reports/create`, `/reports/history`, `/reports/export` | PASS-PARTIAL | backend tests cover service/API | UI report history / daily report buttons need browser smoke |
| Automation | `/automation/daily-report`, `/ocr-posting`, `/reconcile`, `/alerts`, `/approval`, `/retry`, `/close-cycle` | PASS-PARTIAL | backend tests cover automation paths | UI smoke currently covers close-cycle only |
| Promo/XAU bridge | `/promo/campaigns`, `/promo/events`, `/promo/metrics` | PASS-PARTIAL | backend tests cover promo service/API | UI only has `查看 Promo 指標`; campaign/event UI not present |
| Ops | `/ops/status`, `/health/ready`, `/system/capabilities`, `/audit/search` | PASS-SMOKE | UI smoke covers capabilities, audit search, report history, ops status | Live backend proxy smoke still desirable |
| Telegram | `POST /telegram/webhook` | NEEDS-SMOKE | route exists and supports token guard | Need mock test evidence that it works without real Telegram send when token absent |
| Redis orchestration | `/api/v1/orchestration/*`, `WS /ws/trace/{trace_id}` | PASS-BACKEND | `backend/tests/test_orchestration.py` covers state, timeline, websocket echo | Not yet exposed in frontend dashboard UI |

### BuyerOS button/action coverage

| UI action | Status | Current evidence | Gap |
|---|---|---|---|
| 檢查系統健康 | PASS-PARTIAL | visible and route exists | live browser smoke still needed |
| 查看 AI 狀態 | PASS-PARTIAL | Playwright smoke covers provider row | none for real backend in this pass |
| 查看任務列表 | PASS-SMOKE | route exists | smoke verifies task list via task board refresh path |
| 刷新專案清單 | PASS-PARTIAL | project list smoke exists | real backend smoke still needed |
| 選擇風格/theme switch | PASS-PARTIAL | existing UI smoke previously covered | no fresh evidence in this M0 pass |
| 派工並寫回記憶 | NEEDS-SMOKE | frontend handler exists | existing smoke uses create plan, not dispatch submit |
| 只生成 Plan | PASS-PARTIAL | Playwright smoke covers mocked route | live backend smoke needed |
| Run 已選 Plan 下一步 | PASS-SMOKE | Playwright smoke covers mocked next step | live backend smoke still needed |
| 一鍵 Run All | PASS-SMOKE | smoke verifies `POST /tasks/task-ui/run_all` | live backend smoke still needed |
| 查看 Session Context | PASS-SMOKE | smoke verifies `GET /context/session/sess-qa-1` | live backend smoke still needed |
| 任務板：分工/開始/完成 | PASS-SMOKE | smoke covers all three buttons | live backend smoke still needed |
| buyer_ai quick actions | PASS-SMOKE | smoke covers daily report, report history, OCR, reconcile, alerts, approval, retry, close-cycle | live backend smoke still needed |
| commerce quick actions | PASS-SMOKE | smoke verifies form prefill for live selling and finance task | no cross-line mutation; prefill only |
| xau quick actions | PASS-SMOKE | smoke verifies promo metrics result and task prefill | live backend smoke still needed |
| ops links | PASS-SMOKE | smoke covers report history, audit log, capabilities, ops status | live backend smoke still needed |

### Immediate BuyerOS next tasks

1. Review/merge PR #20 when user confirms this smoke coverage belongs in BuyerOS mainline.
2. Decide whether Redis orchestration needs frontend UI in this phase; backend is present, but dashboard does not yet expose it as a user-facing panel.
3. Continue functional inventory for CLOTH and XAU before claiming the whole project is complete.

### BuyerOS M1 smoke coverage update

Branch:
- `/Users/rubykan/Downloads/buyeros-production-repo-v8` branch `codex/buyeros-m1-ui-smoke`

Draft PR:
- https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/pull/20

Commit:
- `ff49ef8 test: expand BuyerOS UI smoke coverage`

Validation:
- `cd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend && npm run ui:smoke` → mocked smoke pass; live-proxy spec skipped unless explicitly enabled
- `cd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend && npm run build` → pass
- `cd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend && npm run lint` → pass after build generated `.next/types`
- `bash /Users/rubykan/Downloads/buyeros-production-repo-v8/infra/smoke_ui_live_proxy.sh` → PASS
  - Starts local backend on `127.0.0.1:8010`
  - Starts local frontend on `127.0.0.1:3010`
  - Uses safe fake `BUYEROS_API_KEY=smoke-local-key`, no real `.env` value
  - Verifies UI buttons reach the real local backend through Next proxy
- `python3 /Users/rubykan/Documents/team/automation/run.py check --repo buyeros` → PASS for all checks, but deploy gate blocked until this branch/config work is committed/merged
  - backend pytest: 236 passed
  - frontend lint: pass
  - frontend build: pass
  - UI smoke: 1 passed
  - live backend-proxy UI smoke: 1 passed
  - HTTP runtime smoke: dashboard shell + ops anchor pass

Notes:
- Mocked UI smoke proves buttons are wired to UI feedback/request paths.
- Live backend-proxy smoke proves the main M1 controls reach a real local backend via the Next proxy. It still uses local in-memory state and a fake API key; no production deploy or external mutation.
- GitHub PR #20 CI is green: backend-test, backend-lint, backend-typecheck, docker-build, frontend-build, docker-smoke, frontend-smoke.

### Latest M0 evidence commands

```bash
git -C /Users/rubykan/Downloads/buyeros-production-repo-v8 status --short
rg --files /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend
rg --files /Users/rubykan/Downloads/buyeros-production-repo-v8/backend
rg -n "@(app|router)\\.(get|post|websocket)|/projects|/tasks|/memory|/ops|/automation|/reports|/promo" backend/app
rg -n 'button|id="|#ops|#projects|#dispatch|#memory' frontend/app/page.tsx frontend/tests/buyeros-ui.smoke.spec.ts
```

## Three-line boundary cleanup — 2026-05-26

Canonical lines are now:

| Line | Canonical ID | Boundary |
|---|---|---|
| Buyer AI 中樞 | `buyer_ai` | BuyerOS / AI Team / Context Hub / Telegram / Task Dispatcher / 買手 Report / refund reconciliation / OCR posting / manual review |
| Commerce 網店自動系統 | `commerce` | Webshop order / after-sales / payment / inventory / support / shop finance / live selling; supplies commerce data to `buyer_ai` but does not own buyer refund reconciliation |
| XAU 系統 | `xau` | XAU AI live stream / real-time news / script generation / OBS / promo / campaign / conversion / metrics |

Updated BuyerOS docs:
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/README.md`
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/infra/README.md`
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/docs/FAST_REPO_LANDING_PLAN.md`
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/docs/NEXT_STEPS_GO_LIVE_PLAN.md`
- `/Users/rubykan/Downloads/buyeros-production-repo-v8/docs/THREE_SYSTEMS_GO_LIVE_PLAN.md`

Historical note:
- `/Users/rubykan/Desktop/xau/THREE-LINE-DEEP-DIVE-2026-05-23.md` is old evidence and now has a superseded notice. Do not use it as canonical task planning.

Validation note:
- This pass did not run XAU, CLOTH, or BuyerOS tests. It was documentation-only and based on read-only code evidence + report cleanup.

## Automation controller

Shared automation controller added at `/Users/rubykan/Documents/team/automation/`.

BuyerOS policy:
- `check`: backend pytest, frontend lint, frontend build, Playwright UI smoke
- `deploy`: existing `infra/preflight_deploy.sh` then `infra/deploy_and_smoke.sh`
- production target: `root@206.189.116.155` / `/opt/buyeros`
- public URL: `https://buyeros.206.189.116.155.sslip.io`
- rollback adapter: `infra/rollback_vps.sh`

Dry-run result on 2026-05-25 23:04 UTC:
- dirty tree: no
- secret diff: no
- deploy gate: open

Latest automation report on 2026-05-27 17:41 UTC:
- dry-run check: PASS
- branch: `main`
- upstream: `origin/main`
- ahead/behind: 0 / 0
- dirty tree: no
- secret diff: no
- deploy gate: open
- live `gh pr view`: PR #19 merged at `7f1b00b`

---

## New shared direction — Redis orchestration core

User wants all agents to learn the Redis/FastAPI orchestration direction:
- Do **not** create a standalone `main.py`.
- Integrate into existing BuyerOS backend app factory: `/Users/rubykan/Downloads/buyeros-production-repo-v8/backend/app/workflows/main.py`.
- Redis dependency already exists in `backend/requirements.txt`.
- Target behavior:
  - Redis Hash agent state: `buyeros:agent:{agent_id}:state`
  - Redis List trace timeline: `buyeros:trace:{trace_id}:timeline`
  - WebSocket stream: `/ws/trace/{trace_id}`
  - history echo on WebSocket connect
  - current agent state debug endpoint
- Implementation must match existing repo style: small service/router, mounted from `create_app()`, env-driven `REDIS_URL`, tests under `backend/tests/`, no secret logging.
- Treat pasted prototype as conceptual; adapt safely instead of blindly copying.

### Implementation status

**Branch:** `codex/buyeros-redis-orchestration-clean`

**Merged PR:** https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/pull/19

**Merge commit:** `7f1b00b`

**Clean PR commits:**
- `a50ae89` — `feat: add Redis orchestration runtime`
- `6cc8283` — `fix: prevent BuyerOS mobile UI overflow`
- `24054a2` — `fix: make BuyerOS ops controls show results`

Old PR #18 was closed because it included earlier Phase 4/5/6 commits.

Implemented:
- `backend/app/orchestration.py`
  - `POST /api/v1/orchestration/state-update`
  - `GET /api/v1/orchestration/agent/{agent_id}`
  - `GET /api/v1/orchestration/trace/{trace_id}/timeline`
  - `WS /ws/trace/{trace_id}`
  - Redis Hash/List persistence with in-memory fallback
- Mounted from `backend/app/workflows/main.py:create_app()`
- Orchestration status added to `/debug/info` and `/health/ready`
- Tests added in `backend/tests/test_orchestration.py`

Validation:
- `backend/tests/test_orchestration.py` — 4 passed
- Integration/ready subset — 16 passed
- Full backend pytest — 234 passed
- Frontend `npm run lint && npm run build` — passed
- UI smoke `npm run ui:smoke` — 1 passed
- Browser QA — main controls, dispatch flow, project switch, theme switch, mobile overflow, ops controls inline result / fallback checked

---

## Audit mode
Read-only blocker audit only. No source code modified.
Forbidden: commit, stage, deploy, Supabase mutation, VPS mutation, write real secrets.

---

## Audit findings

### Supabase / env requirements

**Already resolved (existing in `.env` files):**
- `SUPABASE_URL` = `https://jnzdklfjdjmhjrhntljp.supabase.co` ✅
- `SUPABASE_KEY` = service role key ✅ (present in .env.production / .env.staging.local)
- `SUPABASE_SERVICE_ROLE_KEY` = service role key ✅ (present in .env.production)
- `SUPABASE_DB_PASSWORD` ✅ (present in .env.production)

**Actually present in `.env.production` (verified 2026-05-25, allowlist check only, no values output):**
| Variable | Status |
|---|---|
| `OPENAI_API_KEY` | ✅ PRESENT in `.env.production` |
| `ANTHROPIC_API_KEY` | ✅ PRESENT in `.env.production` |
| `ELEVENLABS_API_KEY` | ✅ PRESENT in `.env.production` |
| `HEYGEN_API_KEY` | ✅ PRESENT in `.env.production` |

### A-track setup result

| Check | Status |
|---|---|
| Four required key names in `.env.production` | ✅ PRESENT |
| npx Supabase CLI | ✅ Available |
| `supabase secrets set` | ✅ Completed |
| Backend smoke tests | ✅ 225 passed |
| Infra smoke tests | ✅ PASS |
| VPS SSH | ✅ primary + staging |

### Phase 5 GitHub Landing

**Branch:** `codex/buyeros-phase45-p2`

**Commits (in order, ready to push):**
| Commit | Message | Author |
|---|---|---|
| `e1f700d` | fix: restore BuyerOS buyer action controls | Claude |
| `3e82917` | fix: satisfy backend CI checks | Claude |
| `71e667c` | docs: record BuyerOS phase 4 validation | Claude |
| `e04da4e` | test: add BuyerOS restore smoke | Claude |
| `920903b` | test: cover BuyerOS runtime integrations | Claude |
| `50ba33a` | test: cover restore_test.sh exit code branches; update CLOTH status | Claude |

**vs `origin/main` (5 extra commits):**
```
e1f700d → 920903b: BuyerOS Phase 5 integrations + Phase 6 restore smoke
bab0dfc: harden three-line go-live and live task routing (main)
```

**PR evidence files:**
- `docs/GO_LIVE_EVIDENCE.md` — full validation results
- `docs/FAST_REPO_LANDING_PLAN.md` — landing phases
- `backend/tests/test_integration_routing.py` — runtime contracts
- `backend/tests/test_three_line_modules.py` — integration smoke
- `infra/restore_test.sh` — DB restore smoke

**PR status:** Draft PR open — awaiting review + merge

---

## Phase 2 / Phase 6 validation results

| Gate | Status |
|---|---|
| SSH primary/staging | ✅ PASS |
| Backend pytest | ✅ 225 passed |
| Frontend lint/build | ✅ PASS |
| Supabase required secret names | ✅ PASS |
| Production go-live audit | ✅ `Go-live audit OK` |
| Phase 2 runtime contract tests | ✅ 14 passed |
| Phase 6 DB restore smoke | ✅ `RESULT: PASS` |

Phase 2 runtime contracts verified:
- XAU client: `GET /api/news/latest`, `POST /api/ai/script`
- CLOTH client: `GET /api/live/readiness`, `POST /api/live/selling-plan`
- Dispatcher: `xau` → `xau_integration`, `commerce` → `cloth_integration`

---

## Security note

All `.env` files excluded from git (correct). Real secrets only on local machine.
Rotate keys after deployment if machine is shared.

## Next action
1. Review + merge draft PR: https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/compare/main...codex/buyeros-phase45-p2
2. After merge: revoke/replace any setup tokens or third-party keys pasted during BuyerOS handoff
3. Before automated deploy: run `python3 /Users/rubykan/Documents/team/automation/run.py check --repo buyeros`, then only deploy after gates remain open
