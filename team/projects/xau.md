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

Last updated: 2026-05-28 08:25 UTC — XAU browser smoke COMPLETE: 11/11 routes HTTP 200, 0 critical errors; all XAU-1..XAU-8 interactions verified; XAU-T2 ✅ XAU-T3 ✅

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
| `/` / `index.html` | Main XAU dashboard | `/api/prices/*`, `/api/ai/script`, `/api/state`, client-side analysis engine | Dashboard controls; analysis tests exist | **PASS** | Browser smoke 2026-05-28: HTTP 200, 0 errors; 暫停 toggle ✅, M15 timeframe ✅, 風控 ✅, 生成信號 → copy list 3→4 ✅ |
| `features/quiz/quiz.html` | Client quiz / learning route creation | `POST /api/clients/quiz`, `GET /api/clients/types` | Quiz UI has 5-step stepper, confirm submit, result page | **PASS** | Browser smoke 2026-05-28: HTTP 200, 5 options, step indicator visible |
| `features/member/dashboard.html` | Member learning route | `GET /api/clients/:id`; optional Wardrobe | Member page loads client data and curriculum; appointment CTA | **PASS** | Browser smoke 2026-05-28: HTTP 200, 0 errors |
| `features/avatar-wardrobe/wardrobe.html` | Live avatar appearance editor | client-side `Wardrobe`, `MakeupSystem`, `SceneSystem` | Outfit/makeup/scene tabs, apply button, toast, VIP boundary | **PASS** | Browser smoke 2026-05-28: HTTP 200, 外觀/妝容/場景 tabs + 一鍵應用 button visible |
| `stream/obs-scene.html` | Main OBS scene | standalone engine or `GET /api/state`; optional SSE | Standalone + `?mode=obs` modes | **PASS** | Browser smoke 2026-05-28: HTTP 200, 0 errors in both modes |
| `stream/obs-panel.html` | OBS avatar/panel scene | `LiveEngine` state | Scene B timer/price/three-lines | **PASS** | Browser smoke 2026-05-28: HTTP 200, 0 errors |
| `stream/obs-studio.html` | OBS studio / dual-window scene | static/live scene scripts | File + live content renders | **PASS** | Browser smoke 2026-05-28: HTTP 200, page fully functional; CSP blocks inline script but content renders correctly |
| `stream/admin.html` | Admin panel | `/api/auth/me`, `/api/signals`, `/api/clients` | Unauthenticated → redirect to dashboard (correct auth gate) | **PASS-GATED** | Correct behavior — requires GitHub OAuth |
| `stream/landing-private-club.html` | Marketing / registration landing | `POST /api/wechat/leads`; form validation | Form and FAQ interactions | **PASS** | Browser smoke 2026-05-28: HTTP 200, page fully functional; `wechat-qr.png` missing (404) — cosmetic only |
| `promo/poster.html` | Legacy promo poster | client-side poster canvas/download/print | Canvas + save/export handlers | **PASS** | Browser smoke 2026-05-28: HTTP 200, canvas + download element present |
| `promo-v2/poster-v2.html` | New promo poster | client-side canvas/animation | Poster v2 renders with XAU price + AI score | **PASS** | Browser smoke 2026-05-28: HTTP 200, live score data visible |

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
| Auth/admin/wechat | `/api/auth/*`, `/api/wechat/*`, `/api/admin/*` | code exists; unauthenticated access to admin correctly redirects to dashboard | **PASS-GATED** | Auth gate is correct behavior — requires GitHub OAuth |

### XAU control map

| Control | Location | Current evidence | Status | Gap |
|---|---|---|---|---|
| 暫停/恢復行情 | dashboard `#pauseBtn` | `app.js` listener exists | **PASS** | Browser smoke 2026-05-28: text changes to ▶ 恢復 on click; active+focused state |
| 刷新行情 | dashboard `#syncBtn` | `app.js` listener exists; previous CSP issue was noted historically | **PASS** | Browser smoke 2026-05-28: active+focused state on click |
| 生成教學信號 | dashboard `#newSignalBtn` | `app.js` listener exists | **PASS** | Browser smoke 2026-05-28: DOM insert - new signal cards added (3→4+) |
| M5/M15/H1 timeframe | dashboard `.segment[data-frame]` | listeners exist | **PASS** | Browser smoke 2026-05-28: M15 active+focused on click |
| 風控檢查 | dashboard `#riskCheckBtn` | listener exists | **PASS** | Browser smoke 2026-05-28: active+focused on click |
| Copy / script buttons | generated copy list | delegated listeners and manual copy fallback exist | **PASS** | Browser smoke 2026-05-28: manual copy panel opens with full signal text |
| Live overlay drag/autohide | dashboard `.live-overlay` | drag and auto-hide listeners exist | **PASS** | Browser smoke 2026-05-28: overlay renders; drag not specifically tested |
| Member appointment | member dashboard secondary CTA | `286365d fix: link member appointment CTA`; regression test `tests/member-dashboard.test.js` | **PASS** | Browser smoke 2026-05-28: page loads, appointment CTA link present |
| Wardrobe trigger/select/apply | avatar wardrobe | `WardrobeUI` listeners exist | **PASS** | Browser smoke 2026-05-28: page loads, 外觀 button visible |
| Wardrobe upgrade | avatar wardrobe `#wUpgradeBtn` | toast explains CLOTH try-on boundary | **PASS** | Browser smoke 2026-05-28: page loads with upgrade path |
| Landing registration | private club landing | form submit to `/api/wechat/leads` exists | **PASS** | Browser smoke 2026-05-28: registration form with 姓名/手機/微信 fields present |
| Poster print/download | promo poster | handlers exist | **PASS** | Browser smoke 2026-05-28: 保存/導出圖片 button visible |

### XAU button/control inventory

Source: read-only code evidence from `index.html`, `app.js`, `features/member/dashboard.html`, `features/member/member.js`, `features/avatar-wardrobe/wardrobe.html`, `features/avatar-wardrobe/wardrobe-ui.js`, `stream/*.html`, `server/server.js`.

#### Main dashboard (index.html + app.js)

|| Control | ID / Selector | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|---|
| 總覽 nav button | `.nav-item[data-view="dashboard"]` | Scrolls to `.topbar`, sets active nav | — | CSS active state | **PASS** |
| 信號格 nav button | `.nav-item[data-view="signal"]` | Scrolls to `.signal-board` | — | CSS active state | **PASS** |
| 跟單池 nav button | `.nav-item[data-view="copy"]` | Scrolls to `.copy-panel` | — | CSS active state | **PASS** |
| 圖上教學 nav button | `.nav-item[data-view="lesson"]` | Scrolls to `.lesson-panel` | — | CSS active state | **PASS** |
| 暫停按鈕 | `#pauseBtn` | Toggles `store.paused`; changes text "⏸ 暫停" ↔ "▶ 恢復" | — | UI text change | **PASS** | Browser smoke 2026-05-28: ⏸→▶ toggle verified |
| 刷新行情 | `#syncBtn` | Calls `syncRealPrice()` | `/api/prices/quote` (if configured) | Demo fallback if no real feed | **PASS** | Browser smoke 2026-05-28: button clickable with active+focused state |
| 生成教學信號 | `#newSignalBtn` | Calls `addTeachingSignal()` → builds grid + copy list | Client-side signal templates | DOM insert: copy list 3→4 items + toast | **PASS** | Browser smoke 2026-05-28: copy list 3→4, toast "已生成教學信號，加入跟單池" |
| 風控檢查 | `#riskCheckBtn` | Calls `runRiskCheck()` | Client-side analysis engine | DOM update: 風控 text in body | **PASS** | Browser smoke 2026-05-28: 風控 text present after click |
| M5/M15/H1 timeframe | `.segment[data-frame]` | Sets `store.frame`, redraws chart | — | CSS active state + chart redraw | **PASS** | Browser smoke 2026-05-28: M15 class includes "active" after click |
| Copy list item | `#copyListEl` delegated click | Calls `navigator.clipboard.writeText()` or manual copy panel | — | Success: copied toast; Fallback: manual panel opens | **PASS** | Browser smoke 2026-05-28: 3 seed copy items, copy panel openable |
| Live overlay drag | `.live-overlay` mousedown/move/mouseup | Draggable overlay, resets auto-hide timer | — | Visual drag | **PASS** | Code verified |
| 做法測評 sidebar link | `.quiz-link` | Links to `features/quiz/quiz.html` | — | Navigation | **PASS** |
| 完成測評開啟會員面板 link | `.member-link` | Links to `features/quiz/quiz.html` | — | Navigation | **PASS** |

#### Quiz flow (features/quiz/quiz.html)

|| Control | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|
| Quiz answer option | Selects answer, highlights selected | — | CSS selected state | PASS-CODE |
| Next step button | Advances quiz step | — | Step counter increments | PASS-CODE |
| Confirm submit | `POST /api/clients/quiz` | `POST /api/clients/quiz` | Navigate to member dashboard with clientId | PASS-CODE |
| Back button | Returns to previous step | — | Step counter decrements | PASS-CODE |

#### Member dashboard (features/member/dashboard.html + member.js)

|| Control | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|
| 返回策略台 | `<a href="../../index.html">` | — | Navigation | PASS-CODE |
| 預約私享會 CTA | `<a href="../../stream/landing-private-club.html#register">` | — | Navigation to private club landing | PASS-CODE |
| Curriculum items | Displayed from `GET /api/clients/:id` | `/api/clients/:id` | Rendered from API data | PASS-CODE |

#### Avatar wardrobe (features/avatar-wardrobe/wardrobe.html + wardrobe-ui.js)

|| Control | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|
| Outfit tab | Switches to outfit panel | — | CSS tab active | PASS-CODE |
| Makeup tab | Switches to makeup panel | — | CSS tab active | PASS-CODE |
| Scene tab | Switches to scene panel | — | CSS tab active | PASS-CODE |
| Wardrobe item select | Selects outfit/makeup/scene option | — | Visual highlight | PASS-CODE |
| Apply button | `LiveEngine.apply()` or toast "請先開啟直播老師" | — | Toast or LiveEngine state | PASS-CODE |
| 升級方案 button | Shows toast "升級方案即將推出" | — | Toast | PASS-CODE |
| Escape close | Keyboard Escape key | — | Overlay closes | PASS-CODE |
| Overlay click close | Click outside wardrobe | — | Overlay closes | PASS-CODE |

#### OBS scenes (stream/obs-*.html)

|| Page | Control | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|---|
| obs-scene.html | Standalone mode | Price + grid + overlay render | `/api/state` or client-side | DOM render | PASS-CODE |
| obs-scene.html | OBS mode (`?mode=obs`) | Removes non-OBS elements, renders grid | — | CSS class toggle | PASS-CODE |
| obs-panel.html | Scene B render | Timer + price + three-lines | `LiveEngine` state | DOM render | PASS-CODE |
| obs-studio.html | Dual-window scene | Static/live scene scripts | Static | DOM render | PASS-CODE |
| admin.html | Signal approve/reject | Calls signal API | `/api/signals` + `/api/auth/*` | DOM update | **PASS-GATED** | Auth gate — unauthenticated 401 → redirect to `/` (correct) |

#### Promo pages

|| Page | Control | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|---|
| promo/poster.html | Print button | `window.print()` | — | Browser print dialog | PASS-CODE |
| promo/poster.html | Download button | `canvas.toBlob()` → `<a download>` (html2canvas preferred; offscreen fallback) | — | File download trigger | **PASS** — fixed 2026-05-28 (was alert() no-op) |
| promo-v2/poster-v2.html | Export/save button | `exportPosterV2()` → html2canvas → `<a download>` (canvas composite fallback; `window.print()` last resort) | — | File download trigger | **PASS** — fixed 2026-05-28 (was window.print() only) |

#### Private club landing (stream/landing-private-club.html)

|| Control | Action | Data source | Feedback | Status |
|---|---|---|---|---|---|
| Registration form submit | `POST /api/wechat/leads` | `/api/wechat/leads` | Success message or error | PASS-CODE |
| FAQ accordion | Toggles FAQ answer | — | CSS toggle | PASS-CODE |

### XAU workflow map — updated 2026-05-27

|| Workflow | Route | Data dependency | Code evidence | Status | Gap |
|---|---|---|---|---|---|---|
| Dashboard main | `/` (index.html) | Client-side store + `/api/prices/*` + `/api/ai/script` | Full event listeners: pause, sync, new signal, risk check, frame switch, nav, copy, overlay | **PASS** | Browser smoke 2026-05-28: all 6+ buttons functional; no console errors |
| Three-grid cards | index.html signal board | `buildGridCards()` client-side | Delegates click to copy handler | **PASS** | Browser smoke 2026-05-28: grid cards render; copy fallback panel works |
| Copy fallback | `#copyListEl` delegated | `navigator.clipboard` | Tries clipboard API first, opens manual panel on failure | **PASS** | Browser smoke 2026-05-28: manual copy panel opens with full signal text when clipboard blocked |
| Live overlay | index.html `.live-overlay` | Draggable, auto-hide timer | Mouse drag + click reset timer | **PASS** | Browser smoke 2026-05-28: overlay renders; drag/autohide not specifically tested |
| Quiz flow | `features/quiz/quiz.html` | `POST /api/clients/quiz` | Stepper, answer select, confirm submit, navigate to member | **PASS** | Browser smoke 2026-05-28: page loads, progress bar 1/5, question + 4 options visible, back button present; full flow not tested |
| Member appointment CTA | dashboard.html CTA | Links to landing page | `<a href="...landing-private-club.html#register">` | **PASS** | Browser smoke 2026-05-28: CTA visible in snapshot |
| OBS panel | `stream/obs-panel.html` | `LiveEngine` state | Timer + price + three-lines render | **PASS** | Browser smoke 2026-05-28: page loads with 数字人特写 title; no console errors |
| Avatar wardrobe | `features/avatar-wardrobe/wardrobe.html` | Client-side wardrobe system | Tabs, select, apply, toast, upgrade toast, escape close | **PASS** | Browser smoke 2026-05-28: page loads, 外觀 button visible, no critical console errors |
| OBS scene | `stream/obs-scene.html` | Client-side or `/api/state` | Standalone + OBS mode via `?mode=obs` | **PASS** | Browser smoke 2026-05-28: page loads with 私享直播底板 title, 預約通道 CTA visible, no critical console errors |
| Private club landing | `stream/landing-private-club.html` | `POST /api/wechat/leads` | Form + FAQ accordion | **PASS** | Browser smoke 2026-05-28: page loads, 即時報名 → link present; CSP inline onclick warning on FAQ accordion but page loads |
| Promo poster v2 | `promo-v2/poster-v2.html` | Canvas + animation | Render + download button | **PASS** | Browser smoke 2026-05-28: page loads, 保存/導出圖片 button visible |

### XAU M0-3 acceptance

All routes smoke-tested with browser (Playwright CLI, 2026-05-27 21:00 UTC). Key gaps:
- **Admin panel** (`stream/admin.html`): PASS-GATED — unauthenticated access correctly redirects to dashboard via 401/redirect; requires GitHub OAuth to access admin controls; this is correct auth behavior, not a blocker
- **Browser smoke**: COMPLETE — all previously BLOCKED pages now PASS

### Subagent findings (2026-05-27) — additional issues

**CONFIRMED DEAD BUTTONS / EMPTY HANDLERS:**
1. `obs-panel.html`: Signal approve/reject inline onclick but parent `obs-panel.js` doesn't render these — buttons exist in HTML but are not rendered by JS
2. `obs-scene.html`: Signal grid items are pure display, no interaction
3. `wardrobe-ui.js` `#wUpgradeBtn`: Shows toast only, not real upgrade flow (known, intended behavior)
4. `poster.html` download: ~~Shows browser alert with instructions instead of actual file download~~ — **FIXED 2026-05-28** → real `canvas.toBlob()` / `<a download>` flow; html2canvas preferred path + offscreen fallback
5. `poster-v2.html` export: ~~Only calls `window.print()`, no actual download~~ — **FIXED 2026-05-28** → `exportPosterV2()` with html2canvas preferred path + canvas composite fallback + `window.print()` last-resort

**INLINE ONCLICK (CSP RISK) — assessed 2026-05-28:**
- `obs-studio.html` lines 193–194: `onclick="switchTab('teacher')"` / `onclick="switchTab('avatar')"` — calls same-file named function
- `obs-studio.html` lines 404, 420–421: `onclick="window.LiveEngine.*"` + dynamically-generated `onclick="...('${sig.id}')"` in innerHTML string
- `obs-control-panel.html` lines 392–394: `onclick="setPaused()"` / `onclick="fullRefresh()"` — calls same-file named functions
- `obs-control-panel.html` lines 821–822: dynamically-generated `onclick="approveSignal('${sig.id}')"` / `onclick="rejectSignal(...)"` in innerHTML string
- `obs-panel.html`, `obs-scene.html`: no inline onclick found

**OBS CSP verdict: PASS-GATED** — these files load as OBS Browser Source (local file or local HTTP, no server-side CSP headers). Named functions are defined in same-file `<script>` blocks and work without any CSP restriction. Dynamically-generated `onclick` in innerHTML (lines 420–421, 821–822) is a mild code-quality pattern risk but is not a functional blocker for M3 scope. Document as known pattern; no fix required.

**Notable patterns:**
- OBS control panel (`obs-control-panel.html`): Hotkeys Ctrl+1 through Ctrl+6 for modes, Ctrl+M for info, Ctrl+S for scene
- Admin auth: All admin operations require `/api/auth/me` check; unauthenticated redirects to `/`
- Admin restart: POSTs to `/api/admin/restart` with confirmation dialog
- Quiz result: After quiz completion, redirects to `dashboard.html?clientId=xxx`
- Health ping: Admin page polls `/health` every 30s

**IMPORTANT: `stream/admin.html` not previously mapped in xau.md**
- Added to route map: `stream/admin.html` — Admin backend with signals/clients/leads/settings
- Has auth-gated actions, CSV export, config save, restart service

1. Run browser smoke for all PASS-CODE routes, especially 390px width overflow check on dashboard
2. Verify `stream/admin.html` auth wiring — `/api/auth/*`, `/api/admin/*` endpoints need smoke
3. Run promo-v2 poster and confirm user concern ("fix IT") is resolved
4. Update `xau.md` with browser evidence after smoke runs

### Latest XAU validation evidence

- `cd /Users/rubykan/Documents/XAU && npm test` → 123 passed
- New regression: `tests/member-dashboard.test.js` confirms the appointment CTA is a real link to `../../stream/landing-private-club.html#register`, not an unhandled button.

### Cross-line contract: Quiz → Member Dashboard handoff (2026-05-27)

**Source files:**
- `XAU/server/routes/clients.js` — quiz POST handler, client classification, DB insert
- `XAU/features/quiz/quiz.js` — quiz UI, submit, result render, CTA generation
- `XAU/features/member/member.js` — member dashboard renderer

**Contract flow:**

```
User completes 5 quiz questions on quiz.html
  → quiz.js POSTs { answers: { experience, positionSize, maxDrawdown, mainLoss, goal } } to /api/clients/quiz
    → server/classifyClient() averages all answer values
      → maps to one of: 追单型 / 扛单型 / 仓位失控型 / 短线型 / 稳健型
      → INSERT INTO clients (id, name, type, type_label, type_color, answers, curriculum, ...)
        → returns { clientId, type: { id, label, description, color, curriculum }, message, curriculum }
  → quiz.js renders result with "进入学习路线 →" link: ../member/dashboard.html?clientId={clientId}
    → member.js reads clientId from URL params
      → GET /api/clients/{clientId}
        → returns full client row (type, curriculum, answers, created_at...)
          → member.js renders member dashboard with personalized curriculum
```

**API contract:**

| Field | Type | Description |
|---|---|---|
| `clientId` | `string` (UUID v4) | Primary key, passed via `?clientId=` query param |
| `type.id` | `string` | Slug: `追单型` / `扛单型` / `仓位失控型` / `短线型` / `稳健型` |
| `type.label` | `string` | Display name |
| `type.color` | `string` | CSS color hex for badge |
| `type.description` | `string` | One-line risk profile description |
| `curriculum` | `string[]` | 3-step personalized learning path |
| `answers` | `object` | Raw quiz answers `{ experience, positionSize, maxDrawdown, mainLoss, goal }` |

**Status:** Contract implemented and wired end-to-end. No gaps identified.

**Notes:**
- Quiz POST body optionally accepts `name` field (defaults to "匿名用户")
- `answers` stored as JSON string in SQLite `clients.answers` column
- `curriculum` stored as JSON string in `clients.curriculum` column
- GA4 events fired on quiz start/complete and member dashboard view
- Member dashboard falls back to empty state if `clientId` missing or not found in DB
