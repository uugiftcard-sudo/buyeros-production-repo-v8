# BuyerOS Project Detail

## Current status
BuyerOS Redis orchestration runtime: Clean draft PR #19 opened (2026-05-25). Pending review + merge.

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

Latest automation report on 2026-05-25 23:43 UTC:
- backend pytest: 234 passed
- frontend lint/build: pass
- Playwright UI smoke: 1 passed
- HTTP runtime smoke: pass (`/`, `/#ops`)
- deploy gate: blocked because the BuyerOS working tree currently has unrelated dirty docs changes

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

**Draft PR:** https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/pull/19

**Latest commit:** `24054a2` — `fix: make BuyerOS ops controls show results`

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
3. Before automated deploy: clear/classify current dirty docs changes, then run `python3 /Users/rubykan/Documents/team/automation/run.py deploy --repo buyeros`
