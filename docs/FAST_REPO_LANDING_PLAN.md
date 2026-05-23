# BuyerOS Fast Repo Landing Plan

## Goal

最快把 BuyerOS 變成可交付、可部署、可交接的正式 repo。

本計劃不再擴大功能範圍，只處理落地必需事項：

- repo 結構固定
- secrets 不入 repo
- primary / staging 可驗收
- GitHub 可推送
- VPS 可部署
- Telegram / Context / 四系統 smoke 可重跑
- 下一位 AI / developer 可接手

## Current Baseline

已完成並可驗收：

- Backend FastAPI
- Context Hub
- Provider registry / fallback
- Task dispatcher / run_all
- Memory timeline
- Telegram webhook mock smoke
- Next.js admin UI
- Four systems smoke:
  - `report`
  - `commerce`
  - `xau`
  - `ai_team`
- Primary VPS:
  - `https://buyeros.206.189.116.155.sslip.io`
- Staging VPS:
  - backend direct: `http://167.172.60.38:8000`
  - frontend direct: `http://167.172.60.38:3000`
  - temporary HTTPS smoke: `BUYEROS_CURL_INSECURE=1`

## Canonical Repo Scope

This repo is the BuyerOS / AIOS control plane.

It owns:

- shared context and memory
- AI provider routing
- task dispatcher
- operator UI
- business automation API
- deployment scripts
- smoke / audit scripts

It does not directly own:

- CLOTH source code
- XAU standalone site source code
- external provider dashboards

Those are connected as systems or projects through BuyerOS.

## Repo Landing Phases

### Phase 0: Freeze Scope

Deliverable:

- No new feature expansion before repo landing.
- Only fixes allowed:
  - security
  - broken tests
  - deploy failure
  - smoke failure
  - secret leakage

Acceptance:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
git status --short
```

Expected:

- dirty files are known and intentional
- no real secrets are staged

### Phase 1: Secret Hygiene

Deliverable:

- Real env files stay local only:
  - `.env`
  - `.env.production`
  - `.env.production.local`
  - `.env.staging.local`
  - `.staging_root_password.local`
- Templates stay tracked:
  - `.env.example`
  - `.env.production.template`
  - `docs/PRODUCTION_INPUTS.md`

Acceptance:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
git check-ignore -v .env .env.production .env.production.local .env.staging.local .staging_root_password.local
git diff --cached | rg -n "(sk-|AAFD|service_role|TELEGRAM_BOT_TOKEN|SUPABASE_KEY|OPENROUTER_API_KEY|ANTHROPIC_API_KEY)" || true
git diff | rg -n "(sk-|AAFD|service_role|TELEGRAM_BOT_TOKEN|SUPABASE_KEY|OPENROUTER_API_KEY|ANTHROPIC_API_KEY)" || true
```

Expected:

- env files are ignored
- no live secret appears in tracked diff

### Phase 2: Local Quality Gate

Deliverable:

- backend tests pass
- backend compiles
- frontend builds
- smoke scripts syntax is valid

Acceptance:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall -q backend/app
bash -n infra/*.sh
cd frontend
./node_modules/.bin/tsc --noEmit
./node_modules/.bin/next build
```

Expected:

- all commands pass

### Phase 3: Staging Gate

Deliverable:

- staging SSH works
- staging backend works
- staging frontend preview works
- staging smoke can run

Acceptance:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
ssh -o BatchMode=yes root@167.172.60.38 'echo staging-key-ok'
API_KEY="$(awk -F= '/^BUYEROS_API_KEY=/{print $2; exit}' .env.staging.local)"
bash infra/smoke_api.sh "http://167.172.60.38:8000" "$API_KEY"
BUYEROS_CURL_INSECURE=1 bash infra/smoke_api.sh "https://buyeros.167.172.60.38.sslip.io" "$API_KEY"
```

Preview:

- UI: `http://167.172.60.38:3000`
- API: `http://167.172.60.38:8000`

Known staging note:

- `sslip.io` may hit Let's Encrypt shared-domain rate limits.
- For browser-trusted staging HTTPS, use a real staging domain.

### Phase 4: Primary Gate

Deliverable:

- primary HTTPS works
- four systems smoke passes
- Telegram webhook mock passes
- Telegram bot token validates
- primary VPS compose is healthy
- staging SSH is available as backup path

Acceptance:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
bash infra/go_live_audit.sh .env.production.local https://buyeros.206.189.116.155.sslip.io root@206.189.116.155 root@167.172.60.38
```

Expected:

```text
Go-live audit OK.
```

### Phase 5: GitHub Landing

Deliverable:

- branch created
- only intended files staged
- no real secrets committed
- commit message describes landing scope

Recommended branch:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
git switch -c codex/buyeros-repo-landing
```

Review before staging:

```bash
git status --short
git diff --stat
git diff -- .gitignore README.md docs infra backend frontend
```

Secret check before commit:

```bash
git diff | rg -n "(sk-|AAFD|service_role|TELEGRAM_BOT_TOKEN|SUPABASE_KEY|OPENROUTER_API_KEY|ANTHROPIC_API_KEY)" || true
```

Stage only intended files:

```bash
git add .gitignore README.md docs infra backend frontend docker-compose.yml Makefile .github .dockerignore .env.example .env.production.template
```

Commit:

```bash
git commit -m "Prepare BuyerOS repo for deployment"
```

Push:

```bash
git push -u origin codex/buyeros-repo-landing
```

## Deployment Model

### Primary

- Host: `206.189.116.155`
- Remote dir: `/opt/buyeros`
- Public URL: `https://buyeros.206.189.116.155.sslip.io`
- Role:
  - production API
  - production UI
  - Telegram webhook
  - Redis runtime
  - provider routing

### Staging

- Host: `167.172.60.38`
- Remote dir: `/root/buyeros`
- Public API fallback: `http://167.172.60.38:8000`
- Public UI fallback: `http://167.172.60.38:3000`
- Role:
  - staging
  - backup target
  - smoke target
  - ops rehearsal

## Go / No-Go Rules

Go if:

- local quality gate passes
- primary go-live audit passes
- staging smoke passes through at least one path
- no real secrets are in tracked diff
- rollback path is known

No-go if:

- backend tests fail
- `/agents/run` or `/tasks/*/run_all` returns 500
- `context write/search/session` fails
- Telegram webhook mock fails
- primary HTTPS fails
- secret appears in git diff

## Immediate Next Actions

1. Run local quality gate.
2. Run staging smoke.
3. Run primary go-live audit.
4. Clean git diff.
5. Create repo landing branch.
6. Commit safe files.
7. Push to GitHub.
8. Use GitHub repo as source of truth for next deploy.

## Operator Shortcuts

Staging preview:

```text
UI  http://167.172.60.38:3000
API http://167.172.60.38:8000
```

Primary preview:

```text
API https://buyeros.206.189.116.155.sslip.io
```

Run full primary gate:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
bash infra/go_live_audit.sh .env.production.local https://buyeros.206.189.116.155.sslip.io root@206.189.116.155 root@167.172.60.38
```

Run staging gate:

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
API_KEY="$(awk -F= '/^BUYEROS_API_KEY=/{print $2; exit}' .env.staging.local)"
bash infra/smoke_api.sh "http://167.172.60.38:8000" "$API_KEY"
```
