# Three Repo Automation — Project Detail

## Summary

建立一個「總控自動化層」管理 BuyerOS、XAU、CLOTH：先跑 repo 狀態、測試、UI smoke、secret scan，再按 repo target 執行部署；所有結果寫回 `state.md` 和各 project md。預設允許自動部署，但只在 gate 全綠、無 dirty risk、無 secret leak 時執行。

## 目標
- 跨 repo 統一 controller：`check` / `deploy` / `report`
- Safety gates 優先：dirty tree / secret pattern / smoke fail → block deploy
- 結果寫回 team state

## 三條 Automation Lane

### `check`
- git status + dirty check
- secret scan（git diff）
- tests/build
- UI smoke（Playwright）
- PR hygiene

### `deploy`
- 只在 `check` 全綠後執行
- 按 repo 走對應 adapter

### `report`
- Markdown summary
- 更新 `state.md` + 各 project md
- 列 pass/fail/blocker

## Repo Deployment Policy

### BuyerOS
- 用現有 script：`infra/preflight_deploy.sh`、`infra/deploy_vps.sh`、`infra/deploy_and_smoke.sh`、`infra/rollback_vps.sh`
- Deploy gate：backend pytest + frontend lint/build + infra smoke 全綠

### XAU
- 只有 Docker：`docker:build` / `docker:up` / `docker:down`
- v1 只做 local Docker deploy，不碰 secrets，不 restore `.env`
- Deploy gate：`npm run test:server` + `node --test tests/analysis-output.test.js` 全綠

### CLOTH
- Target: `cloth.staging.buyeros.com`（nginx reverse proxy on staging VPS `167.172.60.38`）
- v1 deploy adapter 需要建立：
  - `infra/cloth_deploy.sh`：build + scp + nginx reload
  - `infra/cloth_rollback.sh`：restore backup + nginx reload
- Deploy gate：`npm run check` + lint + API smoke 全綠

## Safety Gates

- 任一 repo 有 dirty changes → block deploy
- 任一 diff 命中 secret pattern → block deploy
- BuyerOS：backend pytest + frontend lint/build + infra smoke
- XAU：`npm run test:server` + analysis tests
- CLOTH：`npm run check` + lint + API smoke

## UI Automation

### BuyerOS（Playwright）
- main controls
- ops controls
- dispatch flow
- project switch
- theme switch
- mobile overflow

### XAU
- dashboard
- 三格 signal cards
- copy fallback
- live overlay
- OBS scene console errors

### CLOTH
- products filtering/pagination
- admin basic route
- mobile nav
- API health/readiness

## 關鍵檔案
- Automation controller：`/Users/rubykan/Documents/team/automation/`
- State：`/Users/rubykan/Documents/team/state.md`
- BuyerOS deploy scripts：`buyeros-production-repo-v8/infra/`
- XAU：`buyeros-production-repo-v8/xau/`
- CLOTH：`buyeros-production-repo-v8/cloth/`

## Issues

---

### Issue 1 — CLOTH Deploy Target（HITL）**[CLOTH repo]**

**目標：** 在 staging VPS (`167.172.60.38`) 建立 CLOTH 生產部署 target，subdomain: `cloth.staging.buyeros.com`，使用 nginx reverse proxy。

**需要定義：**
- [ ] CLOTH 部署路徑（建議 `/opt/cloth` 或 `/var/www/cloth`）
- [ ] nginx config：subdomain reverse proxy 到 Node.js service
- [ ] systemd service file 或 PM2 設定
- [ ] rollback script：`infra/cloth_rollback.sh`
- [ ] backup 目錄（建議 `/opt/cloth-backups`）
- [ ] deploy script：`infra/cloth_deploy.sh`

**依賴：** 無

**交付：** `infra/cloth_deploy.sh` + `infra/cloth_rollback.sh` 可執行，deployment smoke test pass

---

### Issue 2 — Safety Gates Engine（AFK）**[BuyerOS repo]**

**目標：** 在 `team/automation/run.py` 的 `check` lane 中實作三個 safety gates，全部 fail 即 block deploy。

**三個 Gates：**
1. `dirty_tree_gate`：任一 repo 有 `git status --porcelain` 非空 → block
2. `secret_pattern_gate`：`git diff` 命中 `config.json` 入面嘅 secret_patterns → block
3. `smoke_fail_gate`：任一 check command exit code ≠ 0 → block

**Acceptance Criteria：**
- [ ] `python3 run.py check --repo all --dry-run` 只列命令，不執行
- [ ] dirty tree → deploy gate = blocked
- [ ] secret diff → deploy gate = blocked
- [ ] smoke fail → deploy gate = blocked

**依賴：** 無

**交付：** `run.py` 已實作三個 gates，各 gate 有明確 error message

---

### Issue 3 — CLOTH Deploy Adapter（AFK）**[CLOTH repo]**

**目標：** 將 `infra/cloth_deploy.sh` + `infra/cloth_rollback.sh`（Issue #1 產出）接入 `team/automation/config.json` 的 CLOTH `deploy_commands`。

**Acceptance Criteria：**
- [ ] `config.json` 中 `cloth.deploy_commands` 非空
- [ ] `python3 run.py deploy --repo cloth` 在 check 全綠時執行 deploy
- [ ] `python3 run.py deploy --repo cloth` 在 check fail 時 block 並輸出 reason
- [ ] rollback adapter 可獨立觸發

**依賴：** Issue #1 完成後才能實作

**交付：** CLOTH deploy 在 controller 中暢通

---

### Issue 4 — UI Smoke Suite（AFK）**[CLOTH repo]**

**目標：** 將三個 repo 嘅 UI smoke 整合入 `team/automation/smoke_http.py`。

**BuyerOS 覆蓋：**
- [ ] main controls
- [ ] ops controls
- [ ] dispatch flow
- [ ] project switch
- [ ] theme switch
- [ ] mobile overflow

**XAU 覆蓋：**
- [ ] dashboard
- [ ] 三格 signal cards
- [ ] copy fallback
- [ ] live overlay
- [ ] OBS scene console errors

**CLOTH 覆蓋：**
- [ ] products filtering/pagination
- [ ] admin basic route
- [ ] mobile nav
- [ ] API health/readiness

**依賴：** 無

**交付：** `smoke_http.py` 支援三個 repo，輸出 pass/fail + 有意義嘅 error message

---

### Issue 5 — GitHub Actions CI Integration（AFK）**[BuyerOS repo]**

**目標：** 在 `buyeros-production-repo-v8` 建立 GitHub Actions workflow，觸發時跑 `check` lane。

**Acceptance Criteria：**
- [ ] `.github/workflows/automation-check.yml` 存在
- [ ] workflow 在 push/PR 時觸發
- [ ] PR status check 顯示 check gate 結果
- [ ] `--dry-run` 模式用於 non-main branches

**依賴：** Issue #2 完成後才能驗證完整

**交付：** GitHub Actions workflow 文件，PR checks 正常顯示

---

### Issue 6 — State Report Writer（AFK）**[CLOTH repo]**

**目標：** `report` lane 將 check 結果寫入 `state.md` + `projects/*.md`。

**Acceptance Criteria：**
- [ ] `python3 run.py report --write-state` 更新 `state.md`
- [ ] 輸出包含每個 repo：status、dirty、secret diff、deploy gate、blockers
- [ ] 不輸出任何 `.env` value、token、private key
- [ ] Markdown 格式化可讀

**依賴：** Issue #2 + Issue #4 完成後才能實作

**交付：** `run.py` 的 `report` mode 可寫入 team state，`latest-report.md` 每次更新

---

## 目前狀態
- Controller 已建立，3 modes（check/deploy/report）完成
- BuyerOS / XAU deploy adapters 完成
- CLOTH deploy adapter ⚠️ BLOCKED：無 production deploy target，working tree dirty

## 測試結果（2026-05-25 dry-run）
- BuyerOS：FAIL（dirty working tree blocks deploy）
- XAU：PASS（gates open）
- CLOTH：FAIL（dirty working tree + secret-like pattern in diff）
