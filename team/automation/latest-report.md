# Automation Report

- Generated: 2026-05-27 19:27 UTC
- Dry run: yes

| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |
|---|---:|---:|---:|---:|---|
| BuyerOS | PASS | no | no | open | - |
| XAU | PASS | no | no | open | - |
| CLOTH | PASS | no | no | open | - |

## BuyerOS

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/buyeros-m1-ui-smoke
upstream: origin/codex/buyeros-m1-ui-smoke
ahead: 0; behind: 0
github pr status: unavailable
```

- PASS (skipped) `backend pytest`: `/Users/rubykan/miniconda3/bin/python -m pytest backend/tests -v --tb=short`
- PASS (skipped) `frontend lint`: `npm run lint`
- PASS (skipped) `frontend build`: `npm run build`
- PASS (skipped) `ui smoke`: `npm run ui:smoke`
- PASS (skipped) `live backend-proxy UI smoke`: `bash infra/smoke_ui_live_proxy.sh`
- PASS (skipped) `http runtime smoke`: `python3 with_server.py --cwd /Users/rubykan/Downloads/buyeros-production-repo-v8/frontend --command 'npm run dev -- --hostname 127.0.0.1 --port 3000' --ready-url http://127.0.0.1:3000 -- python3 smoke_http.py buyeros --base-url http://127.0.0.1:3000`

## XAU

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: codex/xau-dashboard-live-ui
upstream: origin/codex/xau-dashboard-live-ui
ahead: 0; behind: 0
github pr status: unavailable
```

- PASS (skipped) `server tests`: `npm run test:server`
- PASS (skipped) `analysis output tests`: `node --test tests/analysis-output.test.js`
- PASS (skipped) `http ui smoke`: `python3 with_server.py --cwd /Users/rubykan/Documents/XAU --command 'PORT=3002 npm run dev' --ready-url http://127.0.0.1:3002/health -- python3 smoke_http.py xau --base-url http://127.0.0.1:3002`

## CLOTH

- PASS `PR hygiene`: `git branch/upstream/ahead-behind + gh pr status`

```text
branch: cursor/github-actions-workflows
upstream: origin/cursor/github-actions-workflows
ahead: 0; behind: 0
github pr status: unavailable
```

- PASS (skipped) `type/build check`: `npm run check`
- PASS (skipped) `lint`: `npm run lint`
- PASS (skipped) `api smoke`: `node --test scripts/api-smoke.test.mjs`
- PASS (skipped) `validation errors`: `node --test scripts/api-validation-errors.test.mjs`
- PASS (skipped) `market persistence`: `node --test scripts/product-market-persistence.test.mjs`
- PASS (skipped) `products filtering pagination`: `node --test scripts/products-filter-pagination.test.mjs`
- PASS (skipped) `mobile nav contract`: `node --test scripts/mobile-nav-contract.test.mjs`
- PASS (skipped) `http api/ui smoke`: `python3 with_server.py --cwd /Users/rubykan/Documents/CLOTH --command 'PORT=3001 npm run dev --workspace=api' --ready-url http://127.0.0.1:3001/api/health -- python3 smoke_http.py cloth --base-url http://127.0.0.1:3001`
