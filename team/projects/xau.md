# XAU Project Detail

## Current status
XAU is marked completed in shared state, with local dev server previously noted at `http://127.0.0.1:3002/`.

## Automation controller

Shared automation controller added at `/Users/rubykan/Documents/team/automation/`.

XAU policy:
- `check`: `npm run test:server` and `node --test tests/analysis-output.test.js`
- `deploy`: local Docker only via `npm run docker:build` and `npm run docker:up`
- rollback/stop: `npm run docker:down`

Dry-run result on 2026-05-25 23:04 UTC:
- dirty tree: no
- secret diff: no
- deploy gate: open

Latest automation report on 2026-05-25 23:43 UTC:
- `npm run test:server`: pass
- `node --test tests/analysis-output.test.js`: pass
- HTTP UI smoke with temporary `PORT=3002 npm run dev`: pass for dashboard, OBS scene, and `/health`
- deploy gate: open for local Docker target

Update on 2026-05-26:
- Dirty wardrobe/member/promo files classified as XAU live avatar and poster work, not CLOTH customer try-on.
- Commit `ab1ef39 fix: separate live avatar styling from try-on` landed on `codex/xau-dashboard-live-ui`.
- Verification: `npm test` passed with 121 tests; `git diff --check` passed.
- Latest automation dry-run: XAU PASS, no dirty diff, no secret diff, deploy gate open.

## Safety notes
- Do not restore `.env`, runtime DB, or generated signal data.
- Production deploy target/domain is not defined in v1; Docker deploy is local only.
