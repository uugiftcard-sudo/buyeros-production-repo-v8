# 三 Repo 自動化計劃案

## Summary
建立一個「總控自動化層」管理 BuyerOS、XAU、CLOTH：先跑 repo 狀態、測試、UI smoke、secret scan，再按 repo target 執行部署；所有結果寫回 `/Users/rubykan/Documents/team/state.md` 和各 project md。預設允許自動部署，但只在 gate 全綠、無 dirty risk、無 secret leak 時執行。

## Key Changes
- 在 `/Users/rubykan/Documents/team/automation/` 建立跨 repo controller，不放 secrets，只放 repo 路徑、命令、部署 policy、report template。
- 三條 automation lane：
  - `check`：git status、secret scan、tests/build、browser/UI smoke、PR hygiene。
  - `deploy`：只在 `check` 全綠後執行對應 repo deploy adapter。
  - `report`：輸出 Markdown summary，更新 team state，列 pass/fail/blocker。
- Repo deployment policy：
  - BuyerOS：使用現有 `infra/preflight_deploy.sh`、`infra/deploy_vps.sh`、`infra/deploy_and_smoke.sh`、`infra/rollback_vps.sh`；production target 為已存在 VPS。
  - XAU：目前只發現 `docker:build` / `docker:up` / `docker:down`；v1 自動部署限定為 Docker/local target，不碰 secrets，不恢復 `.env`。
  - CLOTH：目前無 production deploy script；v1 自動化只做到 build/smoke/PR-ready。若要 production deploy，先新增明確 deploy target，否則 deploy lane 對 CLOTH 回報 blocker。

## Safety gates
- 任一 repo 有未分類 dirty changes，不 deploy。
- 任一 diff 命中 secret pattern，不 deploy。
- BuyerOS deploy 前必跑 backend pytest、frontend lint/build、infra smoke。
- XAU deploy 前必跑 `npm run test:server` 和 `node --test tests/analysis-output.test.js`。
- CLOTH deploy 前必跑 `npm run check`、`npm run lint`、API smoke tests。

## UI automation
- BuyerOS：Playwright 覆蓋 main controls、ops controls、dispatch flow、project switch、theme switch、mobile overflow。
- XAU：dashboard，三格 signal cards、copy fallback、live overlay、OBS scene console errors。
- CLOTH：products filtering/pagination、admin basic route、mobile nav、API health/readiness。

## Scheduling
- GitHub PR checks 用 GitHub Actions。
- 本機每日/每 30 分鐘狀態監控可用 Codex app automation，但記錄為「app 關閉會停」。
- Production deploy 不做定時自動，只做手動觸發 `deploy` mode。

## Test Plan
- Dry run：
  - `python team/automation/run.py check --repo all --dry-run`
  - 確認只列命令，不執行 deploy。
- Local full check：
  - BuyerOS backend/frontend/UI smoke 全綠。
  - XAU server + analysis tests 全綠。
  - CLOTH check/lint/API smoke 全綠。
- Failure simulation：
  - dirty tree → block deploy。
  - secret pattern in diff → block deploy。
  - CLOTH deploy target missing → blocker，不嘗試猜部署。
  - BuyerOS smoke fail → stop and call rollback adapter only if deploy already started。
- Report validation：
  - `state.md` 顯示每 repo 最新 status、last command、result、blockers。
  - 不輸出任何 `.env` value、token、private key。

## Assumptions
- 自動部署權限只對已有明確 deploy script 的 repo 生效；目前只有 BuyerOS 最完整。
- XAU/CLOTH 若要 production deploy，需要先定 target/domain/rollback script。
- 所有 automation artifacts 放在 `Documents/team/automation/`，不混入三個 product repo。
- Deploy gate 預設嚴格：有疑點就 stop，不靠 AI 猜。