# Team Project State

## Last updated
2026-05-27 19:30 UTC by Codex — BuyerOS PR #20 CI verified green; CLOTH M0 route/control map added; functional completion project remains active

## Blockers ⚠️
- Rotate/revoke any setup tokens or third-party keys pasted during BuyerOS handoff (PR merge 後做)
- CLOTH deploy target selected as `/opt/cloth`, service manager selected as systemd; remaining blocker is real VPS/nginx/systemd validation and DNS reachability
- GitHub PR status from automation output remains unavailable, but live `gh pr status` was checked manually:
  - BuyerOS PR #19: merged
  - CLOTH PR #9: merged

## Active Tasks

### Active Detailed Project 🔄 FUNCTION_COMPLETION_PROJECT
- [🔄 ACTIVE] Current detailed project is `/Users/rubykan/Documents/team/automation/FUNCTION_COMPLETION_PROJECT.md`
- [🎯 SCOPE] Complete usable product functionality across `buyer_ai / commerce / xau`; repo hygiene or merged PRs are not enough
- [0️⃣ NEXT] First batch: Milestone 0 functional inventory — page/API/button map for BuyerOS, CLOTH, and XAU
- [✅ PASS] BuyerOS branch `codex/buyeros-m1-ui-smoke`: `python3 /Users/rubykan/Documents/team/automation/run.py check --repo buyeros` PASS
- [✅ PR] BuyerOS draft PR #20 opened: https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/pull/20
- [✅ PARTIAL] BuyerOS M0/M1 UI smoke now covers project switch, dispatch plan, run_all, memory/timeline, report, buyer_ai quick actions, commerce/xau quick actions, task board, ops controls
- [✅ PASS] BuyerOS live backend-proxy UI smoke now starts local backend/frontend with fake `BUYEROS_API_KEY=smoke-local-key` and verifies main controls through Next proxy
- [✅ CI] BuyerOS PR #20 is open as draft, mergeable, and GitHub CI checks are green: backend-test, backend-lint, backend-typecheck, docker-build, frontend-build, docker-smoke, frontend-smoke
- [✅ PASS-CODE] CLOTH M0 route/control map added to `/Users/rubykan/Documents/team/projects/cloth.md`; Support/Inventory frontend are flagged as mockStorage-backed until browser/API wiring is verified
- [1️⃣ NEXT] Review/merge PR #20 when ready, then continue Milestone 0 inventory for XAU pages
- [2️⃣ NEXT] Then Milestone 2: CLOTH `commerce` usable loop — products, cart, wishlist, orders, finance, inventory, support, admin, mobile nav
- [3️⃣ NEXT] Then Milestone 3: XAU usable loop — dashboard, member pages, OBS/live overlay, teacher appearance, campaign/conversion/metrics
- [🛑 NOTE] This is not the removed `team/multi-agent-system/` prompt system and not just the older `TRI_REPO_PLAN.md`
- [🧪 ACCEPTANCE] Each feature needs UI/API/test evidence plus clean git hygiene; no secrets, no production env mutation, no dirty deploy
- [ℹ️ EVIDENCE] 2026-05-27 17:41 dry-run: BuyerOS/XAU/CLOTH PASS/open, dirty=no, secret diff=no; this proves hygiene only, not feature completion

### Control Room Boundary ✅ UPDATED
- [✅ DONE] Refund reconciliation / refund matching / OCR posting / manual review are owned by `buyer_ai`
- [✅ DONE] `commerce` only supplies webshop order, after-sales, payment, inventory, and support data for reconciliation
- [✅ DONE] Buyer report remains separate from commerce/shop work
- [✅ DONE] BuyerOS docs boundary cleanup: README / infra README / landing / next-step docs now use `buyer_ai`, `commerce`, `xau`
- [ℹ️ NOTE] `/Users/rubykan/Desktop/xau/THREE-LINE-DEEP-DIVE-2026-05-23.md` is marked superseded; it is read-only historical evidence, not canonical planning
- [ℹ️ NOTE] This boundary cleanup did not run XAU / CLOTH / BuyerOS tests; it was documentation-only based on read-only code evidence

### Three Repo Automation ✅ CONTROLLER ADDED
- [✅ DONE] Shared controller created at `/Users/rubykan/Documents/team/automation/`
- [✅ DONE] Modes: `check`, `deploy`, `report`
- [✅ DONE] Safety gates: dirty tree, secret-like git diff, failing checks block deploy
- [✅ DONE] Command timeout added via `command_timeout_seconds` and process-group kill on timeout
- [✅ DONE] Secret scan false-positive handling narrowed to added diff lines and known env-name references
- [✅ DONE] BuyerOS deploy adapter: existing VPS deploy + smoke scripts
- [✅ DONE] XAU deploy adapter: local Docker only
- [✅ DONE] CLOTH deploy adapter: `infra/cloth_deploy.sh`, `infra/cloth_rollback.sh`, systemd service, nginx template wired into automation config
- [✅ DONE] 30-minute Codex heartbeat created: `three-repo-automation-monitor`（app/session 關閉會停）
- Latest dry-run validation: 2026-05-27 17:41 UTC BuyerOS/XAU/CLOTH PASS/open; secret diff is `no` for all three repos; all three tracked branches are 0 ahead / 0 behind

### CLOTH ✅ PHASE 2 COMPLETE
- [✅ DONE] P2：GET /api/products filtering + pagination
- [✅ DONE] Query: market/status/brand/category/condition/minPrice/maxPrice/search/page/limit/sort
- [✅ DONE] Regression test: `scripts/products-filter-pagination.test.mjs` (2 cases, build+start mode)
- [✅ DONE] All smoke: products-filter-pagination + api-smoke + api-validation-errors + market-persistence + mobile-nav-contract + lint

### CLOTH Phase 1 ✅ COMPLETED
- [✅ DONE] P1-A Mobile Responsive Navigation
- [✅ DONE] P1-B product market persistence
- [✅ DONE] P1-C input validation + structured error handling
- [✅ DONE] P1-D API smoke contracts

### BuyerOS ✅ Redis Orchestration PR merged
- [✅ DONE] PR #19 `BuyerOS Redis orchestration runtime` merged at `7f1b00b`
- [✅ DONE] Local repo is on `main`, 0 ahead / 0 behind, clean

### XAU ✅ COMPLETED
- [✅ DONE] Dark luxury UI 美化（Premium Bloomberg-style dark theme）
- [✅ DONE] All fixes：.gitignore / clipboard fallback / Quiz API base / member entry clientId
- [✅ DONE] Boundary copy fix: XAU wardrobe/member now labels feature as live avatar appearance, not CLOTH customer try-on (`ab1ef39`)
- [✅ DONE] 119 npm tests pass，browser smoke pass
- Dev server：http://127.0.0.1:3002/

### CLOTH Phase 0 ✅ COMPLETED
- [✅ DONE] SQLite persistence foundation (`api/src/db/index.ts`)
- [✅ DONE] Migration (`api/src/db/migrations/001_initial.sql`)
- [✅ DONE] Product/Order store → SQLite-backed
- [✅ DONE] Finance API → SQLite-backed CRUD + stats
- [✅ DONE] Inventory API → SQLite-backed items + transactions + inbound/outbound
- [✅ DONE] Support API → SQLite-backed tickets + messages + FAQs
- [✅ DONE] `.gitignore` 加咗 `api/data/`，本地 DB 不入 repo
- [✅ DONE] Dependencies: `better-sqlite3` + `@types/better-sqlite3`

### CLOTH Phase 1 ✅ COMPLETED
- [✅ DONE] P1-A Mobile Responsive Navigation
- [✅ DONE] P1-B product market persistence
- [✅ DONE] P1-C input validation + structured error handling
- [✅ DONE] P1-D API smoke contracts

### BuyerOS ✅ PHASE 2 + PHASE 6 COMPLETE
- ✅ All Phase 2 runtime contracts verified
- ✅ Phase 4 go-live audit: Go-live audit OK
- ✅ Phase 6 DB restore smoke: RESULT: PASS
- ✅ PR #15 + PR #16 merged

### BuyerOS Phase 5 ✅ IN PROGRESS — Draft PR Open
- ✅ Branch `codex/buyeros-phase45-p2` pushed to GitHub (`50ba33a`)
- ✅ Draft PR opened: BuyerOS Phase 5: Integration smoke + Phase 6 DB restore smoke
- 🔜 Review + merge → then revoke setup tokens

### BuyerOS Redis Orchestration ✅ IN PROGRESS — Draft PR Open
- ✅ Clean branch `codex/buyeros-redis-orchestration-clean` pushed (`24054a2`)
- ✅ Clean draft PR opened: https://github.com/uugiftcard-sudo/buyeros-production-repo-v8/pull/19
- ✅ Old PR #18 closed because it included earlier Phase 4/5/6 commits
- ✅ Backend pytest: 234 passed
- ✅ UI QA: main controls, dispatch flow, project switch, theme switch, mobile overflow fix, ops controls no-JS fallback, frontend build + Playwright smoke
- 🔜 Review + merge

<!-- ISSUES_START -->

## GitHub Issues — Three Repo Automation

---

### Issue 1 — CLOTH Deploy Target（HITL）**[CLOTH repo]**
```markdown
## CLOTH VPS Deploy Target

### 目標
在 staging VPS (`167.172.60.38`) 建立 CLOTH 生產部署 target，subdomain: `cloth.staging.buyeros.com`，使用 nginx reverse proxy。

### 需要定義
- [x] CLOTH 部署路徑：`/opt/cloth`
- [x] nginx config template：subdomain reverse proxy 到 Node.js service
- [x] systemd service file
- [x] rollback script：`infra/cloth_rollback.sh`
- [x] backup 目錄：`/opt/cloth-backups`
- [x] deploy script：`infra/cloth_deploy.sh`

### 依賴
無（此 issue 不 blocked by others）

### 交付
- `infra/cloth_deploy.sh` 可執行
- `infra/cloth_rollback.sh` 可執行
- nginx/systemd/deployment smoke still require real VPS validation
```

---

### Issue 2 — Safety Gates Engine（AFK）**[BuyerOS repo]**
```markdown
## Safety Gates Engine

### 目標
在 `team/automation/run.py` 的 `check` lane 中實作三個 safety gates，全部 fail 即 block deploy。

### 三個 Gates
1. **dirty_tree_gate**：任一 repo 有 `git status --porcelain` 輸出非空 → block
2. **secret_pattern_gate**：`git diff` 命中 `config.json` 入面嘅 secret_patterns 任一 → block
3. **smoke_fail_gate**：任一 check command exit code ≠ 0 → block

### Acceptance Criteria
- [x] `python3 run.py check --repo all --dry-run` 只列命令，不執行
- [x] `python3 run.py check --repo all` 在 dirty tree 時 deploy gate = blocked
- [x] secret diff false-positive from env-name references no longer blocks
- [x] `python3 run.py check --repo all` 在 smoke fail 時 deploy gate = blocked
- [x] timeout returns exit code `124` and blocks deploy

### 依賴
無

### 交付
- `run.py` 已實作三個 gates
- 各 gate 有明確 error message 輸出
```

---

### Issue 3 — CLOTH Deploy Adapter（AFK）**[CLOTH repo]**
```markdown
## CLOTH Deploy Adapter

### 目標
將 `infra/cloth_deploy.sh` + `infra/cloth_rollback.sh`（Issue #1 產出）接入 `team/automation/config.json` 的 CLOTH `deploy_commands`。

### Acceptance Criteria
- [x] `config.json` 中 `cloth.deploy_commands` 非空
- [x] `python3 run.py deploy --repo cloth --dry-run` 在 check 全綠時 reaches deploy command
- [x] `python3 run.py deploy --repo cloth` 在 check fail 時 block 並輸出 reason
- [x] rollback adapter wired in config

### 依賴
Issue #1 完成後才能實作

### 交付
- `config.json` 已更新
- CLOTH deploy 在 controller 中暢通
```

---

### Issue 4 — UI Smoke Suite（AFK）**[CLOTH repo]**
```markdown
## UI Smoke Suite

### 目標
將三個 repo 嘅 UI smoke 整合入 `team/automation/smoke_http.py`。

### BuyerOS 覆蓋
- [ ] main controls
- [ ] ops controls
- [ ] dispatch flow
- [ ] project switch
- [ ] theme switch
- [ ] mobile overflow

### XAU 覆蓋
- [ ] dashboard
- [ ] 三格 signal cards
- [ ] copy fallback
- [ ] live overlay
- [ ] OBS scene console errors

### CLOTH 覆蓋
- [ ] products filtering/pagination
- [ ] admin basic route
- [ ] mobile nav
- [ ] API health/readiness

### 依賴
無

### 交付
- `smoke_http.py` 支援三個 repo 嘅 UI smoke
- 輸出 pass/fail + 有意義嘅 error message
```

---

### Issue 5 — GitHub Actions CI Integration（AFK）**[BuyerOS repo]**
```markdown
## GitHub Actions CI Integration

### 目標
在 `buyeros-production-repo-v8` 建立 GitHub Actions workflow，觸發時跑 `check` lane。

### Acceptance Criteria
- [ ] `.github/workflows/automation-check.yml` 存在
- [ ] workflow 在 push/PR 時觸發
- [ ] PR status check 顯示 check gate 結果
- [ ] `--dry-run` 模式用於 non-main branches

### 依賴
Issue #2 完成後才能驗證完整

### 交付
- GitHub Actions workflow 文件
- PR checks 正常顯示
```

---

### Issue 6 — State Report Writer（AFK）**[CLOTH repo]**
```markdown
## State Report Writer

### 目標
`report` lane 將 check 結果寫入 `state.md` + `projects/*.md`。

### Acceptance Criteria
- [ ] `python3 run.py report --write-state` 更新 `state.md`
- [ ] 輸出包含每個 repo：status、dirty、secret diff、deploy gate、blockers
- [ ] 不輸出任何 `.env` value、token、private key
- [ ] Markdown 格式化可讀

### 依賴
Issue #2 + Issue #4 完成後才能實作

### 交付
- `run.py` 的 `report` mode 可寫入 team state
- `latest-report.md` 每次更新
```

<!-- ISSUES_END -->

<!-- AUTOMATION_STATUS_START -->
# Automation Report

- Generated: 2026-05-27 17:41 UTC
- Dry run: yes

| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |
|---|---:|---:|---:|---:|---|
| BuyerOS | PASS | no | no | open | - |
| XAU | PASS | no | no | open | - |
| CLOTH | PASS | no | no | open | - |

**Note:** BuyerOS PR #19 merged at `7f1b00b`; CLOTH PR #9 merged at `7256511`. BuyerOS branch `main`, XAU branch `codex/xau-dashboard-live-ui`, and CLOTH branch `cursor/github-actions-workflows` are all 0 ahead / 0 behind. Automation's internal `gh pr status` field still reports unavailable, but live PR merge evidence has been verified with `gh pr view`.
<!-- AUTOMATION_STATUS_END -->
