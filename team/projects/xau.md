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

## Functional completion project — Milestone 0 UI map

Last updated: 2026-05-27 19:35 UTC by Codex.

Source plan:
- `/Users/rubykan/Documents/team/automation/FUNCTION_COMPLETION_PROJECT.md`

Important correction:
- XAU is not function-complete just because server/analysis tests and HTTP smoke pass.
- This map is code evidence only. Browser route/control smoke still needs to be run before final completion.
- AI teacher wardrobe / appearance belongs to XAU live avatar styling only. CLOTH customer photo upload try-on belongs to `commerce`, not XAU.

Frontend/API sources:
- `/Users/rubykan/Documents/XAU/index.html`
- `/Users/rubykan/Documents/XAU/app.js`
- `/Users/rubykan/Documents/XAU/features/member/dashboard.html`
- `/Users/rubykan/Documents/XAU/features/member/member.js`
- `/Users/rubykan/Documents/XAU/features/avatar-wardrobe/wardrobe.html`
- `/Users/rubykan/Documents/XAU/features/avatar-wardrobe/wardrobe-ui.js`
- `/Users/rubykan/Documents/XAU/stream/*.html`
- `/Users/rubykan/Documents/XAU/server/server.js`

### XAU route map

| Route / page | Purpose | Data dependency | Current evidence | Status | Gap / next action |
|---|---|---|---|---|---|
| `/` / `index.html` | Main XAU dashboard | `/api/prices/*`, `/api/ai/script`, `/api/state`, client-side analysis engine | Dashboard controls and grid/copy/overlay code exist; analysis tests exist | PASS-CODE | Needs browser smoke for all dashboard buttons and 390px overflow |
| `features/quiz/quiz.html` | Client quiz / learning route creation | `POST /api/clients/quiz`, `GET /api/clients/types` | Server tests cover quiz API; quiz UI has stepper, confirm submit, result link | PASS-CODE | Needs browser smoke from answer flow to member route |
| `features/member/dashboard.html?clientId=...` | Member learning route | `GET /api/clients/:id`; optional Wardrobe integration | Member page loads client data and curriculum; appointment CTA now links to private-club registration | FIXED-CODE | Needs browser smoke from quiz result to member page and CTA navigation |
| `features/avatar-wardrobe/wardrobe.html` | Live avatar appearance editor | client-side `Wardrobe`, `MakeupSystem`, `SceneSystem`; optional `LiveEngine` | Outfit/makeup/scene tabs, apply button, toast, VIP boundary copy exist | PASS-CODE | Needs browser smoke; verify trigger, select, apply, Escape close, overlay click close |
| `stream/obs-scene.html` | Main OBS scene | standalone engine or `GET /api/state`; optional SSE `/api/state/stream` | README + live-engine support standalone/OBS/SSE modes | PASS-CODE | Needs console-error browser smoke in standalone and `?mode=obs` |
| `stream/obs-panel.html` | OBS avatar/panel scene | `LiveEngine` state | Scene B timer/price/three-lines code exists | PASS-CODE | Needs browser smoke |
| `stream/obs-studio.html` | OBS studio / dual-window scene | static/live scene scripts | File exists in stream suite | PASS-CODE | Needs browser smoke |
| `stream/admin.html` | Admin panel: signals, clients, leads, settings | `/api/auth/me`, `/api/signals`, `/api/clients`, `/api/wechat/leads`, `/api/admin/*` | Admin controls exist, but auth/admin API availability not fully proven in this audit | BLOCKED-PARTIAL | Needs authenticated/browser smoke; verify `/api/admin/*` route wiring before claiming done |
| `stream/landing-private-club.html` | Marketing / registration landing | `POST /api/wechat/leads`; form validation | Form and FAQ interactions exist | PASS-CODE | Needs browser smoke and API result check |
| `promo/poster.html` | Legacy promo poster | client-side poster canvas/download/print | Print/download handlers exist | PASS-CODE | Needs browser smoke for poster render/download fallback |
| `promo-v2/poster-v2.html` | New promo poster | client-side canvas/animation | Poster v2 scripts exist | PASS-CODE | Needs browser smoke; user previously said "fix IT" here, so verify manually before done |

### XAU API map

| API area | Endpoint(s) | Current evidence | Status |
|---|---|---|---|
| Health/API index | `GET /health`, `GET /api` | `tests/server.test.js` covers both | PASS |
| Prices | `GET /api/prices/quote`, `/history`, `/xau/quote` | server tests cover quote/history | PASS |
| AI script | `GET /api/ai/script/fallback`, `POST /api/ai/script`, `POST /api/ai/signal-interpretation` | server tests cover script fallback/error; dashboard uses script generator | PASS-PARTIAL |
| State/OBS | `GET/POST /api/state`, `/api/state/diff`, `/api/state/stream`, `/sync-prices`, `/seed` | server tests cover state; README documents OBS modes | PASS-PARTIAL |
| Clients/quiz | `GET /api/clients/types`, `POST /api/clients/quiz`, `GET /api/clients/:id` | server tests cover types/quiz; member uses client detail | PASS-PARTIAL |
| Signals | `GET/POST /api/signals`, `PATCH /api/signals/:id/status`, pending count | server tests cover GET/POST; admin uses status actions | PASS-PARTIAL |
| TTS | `POST /api/tts`, `/speak-to-file`, `/latest`, `/providers` | server tests cover browser provider and ElevenLabs missing voiceId 400 | PASS |
| News | `GET /api/news/latest`, `POST /api/news/alerts` | server tests cover latest | PASS-PARTIAL |
| Campaigns/metrics | `GET/POST /api/campaigns`, conversion, metrics | server tests cover create/conversion/metrics | PASS |
| Auth/admin/wechat | `/api/auth/*`, `/api/wechat/*`, `/api/admin/*` | code exists, but not fully verified in this audit | BLOCKED-PARTIAL |

### XAU control map

| Control | Location | Current evidence | Status | Gap |
|---|---|---|---|---|
| 暫停/恢復行情 | dashboard `#pauseBtn` | `app.js` listener exists | PASS-CODE | Browser smoke |
| 刷新行情 | dashboard `#syncBtn` | `app.js` listener exists; previous CSP issue was noted historically | PASS-CODE | Browser smoke to ensure no inline onclick/CSP failure |
| 生成教學信號 | dashboard `#newSignalBtn` | `app.js` listener exists | PASS-CODE | Browser smoke |
| M5/M15/H1 timeframe | dashboard `.segment[data-frame]` | listeners exist | PASS-CODE | Browser smoke |
| 風控檢查 | dashboard `#riskCheckBtn` | listener exists | PASS-CODE | Browser smoke |
| Copy / script buttons | generated copy list | delegated listeners and manual copy fallback exist | PASS-CODE | Browser smoke clipboard fallback |
| Live overlay drag/autohide | dashboard `.live-overlay` | drag and auto-hide listeners exist | PASS-CODE | Browser smoke at desktop/mobile sizes |
| Member appointment | member dashboard secondary CTA | `286365d fix: link member appointment CTA`; regression test `tests/member-dashboard.test.js` | FIXED-CODE | Browser smoke still required |
| Wardrobe trigger/select/apply | avatar wardrobe | `WardrobeUI` listeners exist | PASS-CODE | Browser smoke |
| Wardrobe upgrade | avatar wardrobe `#wUpgradeBtn` | toast explains CLOTH try-on boundary | PASS-CODE | Browser smoke |
| Admin signal actions | admin panel | approve/reject/trigger/close/delete buttons exist | BLOCKED-PARTIAL | Needs auth/admin API smoke |
| Landing registration | private club landing | form submit to `/api/wechat/leads` exists | PASS-CODE | Browser smoke/API response |
| Poster print/download | promo poster | handlers exist | PASS-CODE | Browser smoke |

### Immediate XAU next tasks

1. Run browser smoke for dashboard, quiz/member, wardrobe, OBS scenes, admin, landing, poster v2.
2. Verify `stream/admin.html` API dependencies, especially `/api/admin/*`, before marking admin done.
3. Update this file with browser evidence and screenshots/log summary.

### Latest XAU validation evidence

- `cd /Users/rubykan/Documents/XAU && npm test` → 123 passed
- New regression: `tests/member-dashboard.test.js` confirms the appointment CTA is a real link to `../../stream/landing-private-club.html#register`, not an unhandled button.
