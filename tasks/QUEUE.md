# Task Queue — BuyerOS Work Session

> Auto-updated by Claude Code autonomous work session.
> Last updated: 2026-05-23

---

## READY

### BuyerOS — Supabase Audit (P0, needs user action)
- Run `recon/supabase-audit.sql` in Supabase Studio
- Download all 12 result CSVs
- Share results with AI to fill in ARCHITECTURE.md Section 8

### BuyerOS Backup System — Phase 0-3 Setup (needs user action)
- Follow `backup-system/SETUP-PROGRESS.md` phases
- Phase 0: Bitwarden account + gather secrets
- Phase 1: Cloudflare R2 bucket creation
- Phase 2: Supabase test project
- Phase 3: GitHub repo + workflows + manual trigger test

### BuyerOS — Telegram Webhook Verification
- Run `curl` commands from DEPLOY.md Step 6 to verify webhook
- Test `/start` and `/myorders` commands

---

## IN PROGRESS

*(none currently)*

---

## DONE ✅

### 2026-05-23 — Morning Session

- **scrapers**: Fixed 6 ruff lint errors (unused imports), updated `pyproject.toml` to modern `[tool.ruff.lint]` format. All 37 tests pass. Lint clean.
- **XAU**: Started demo server at `http://localhost:4173/`. Verified all key pages: index, obs-scene, quiz, member-dashboard — all 200.
- **CLOTH**: Fixed 3 TypeScript errors (`client.ts` Error.cause compat, `Home.tsx` PaginatedResponse unwrap, `ProductDetail.tsx` null guard). Type check clean.
- **BuyerOS**: Updated `ARCHITECTURE.md` v1.1.1 — confirmed Deno runtime, Supabase Auth, Next.js admin UI, Edge Functions list.
- **CHANGELOG.md**: Updated with all morning session work.

### 2026-05-23 — Afternoon Session (Autonomous)

- **scrapers**: AliExpress scraper — `src/scrapers/aliexpress.py`, `src/models/aliexpress.py`, CLI command added, config.yaml updated. All syntax checked ✅
- **scrapers**: Vinted scraper — `src/scrapers/vinted.py`, `src/models/vinted.py`, CLI command added. All syntax checked ✅
- **XAU**: Real Finnhub price feed — `server/services/priceService.js` (Finnhub → GoldAPI → mock chain), wired into `server.js` startup/shutdown lifecycle. Syntax checked ✅
- **XAU**: `server/routes/prices.js` updated — dual endpoint (legacy + `/xau/quote`), SSE cache sync via EventEmitter
- **BuyerOS/admin**: `app/periods/page.tsx` — 月結管理 full UI with open/close, SQL helpers, 6-step guide
- **BuyerOS/admin**: `app/communications/page.tsx` — 通訊記錄 CRM with channel/direction/tag filters, archive, new entry form
- **BuyerOS/admin**: `app/financials/page.tsx` — SVG P&L bar chart (6-month revenue vs expenses)
- **BuyerOS/admin**: `components/Sidebar.tsx` — added 運營 section + 通訊記錄; fixed `useRouter` import bug in `orders/[id]`
- **BuyerOS**: `supabase/migrations/0004_communications_kyc.sql` — new migration for `communications` and `buyer_documents` tables with full RLS
- **BuyerOS**: `supabase/functions/communications/index.ts` — new Edge Function for CRUD on communications
- **BuyerOS**: `supabase/functions/_shared/index.ts` — added `generateSettlementNumber`, `isValidChannel`, `isValidDirection`
- **CHANGELOG.md**: Updated [Unreleased] section with all new additions

---

## NOTES

- BuyerOS Edge Functions confirmed written in **Deno** (not Node.js)
- CLOTH TypeScript target is ES2020 — do NOT use Error.cause or other ES2022+ features
- XAU server running at localhost:4173 — stop with `pkill -f "http.server 4173"`
- scrapers `amazon_monitor.py` is a standalone script in root — separate from structured `src/scrapers/` CLI
- BuyerOS SETUP-PROGRESS phases 4-6 need VPS SSH access (DigitalOcean 206.189.116.155)

---

## RULES FOR FUTURE SESSIONS

1. Check this file first at session start
2. Items under DONE are already handled — do not repeat
3. Items needing user action: add to queue notes, work around them
4. Always update this file when completing tasks
