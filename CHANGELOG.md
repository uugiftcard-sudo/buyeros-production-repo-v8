# Changelog

All notable changes to this workspace are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **CLOTH**: Multi-market (UK / HK / CN) support — three independent storefronts with market-specific copy, branding, and currency conversion
- **CLOTH**: `src/types/market.ts` — Market types, `MARKET_CONFIGS` (exchange rates, currency symbols, locales), `convertPrice()`, `formatPrice()`
- **CLOTH**: `src/hooks/useMarket.tsx` — `MarketProvider` + `useMarket()` hook; persists active market to localStorage, updates browser URL path
- **CLOTH**: `src/pages/UKHome.tsx` — full British English landing page with GBP pricing (¥CNY × 0.11), EN trust copy, Same-Day UK Delivery messaging
- **CLOTH**: `src/pages/HKHome.tsx` — full Traditional Chinese landing page with HKD pricing (¥CNY × 1.32), bilingual branding
- **CLOTH**: `src/pages/Home.tsx` (CN) — updated to use CN market; all three home pages share CSS via `Home.module.css`
- **CLOTH**: `src/components/Header.tsx` — market selector dropdown (UK🇬🇧 / HK🇭🇰 / CN🇨🇳) with animated dropdown; nav/search/copy adapts per market
- **CLOTH**: `src/components/Footer.tsx` — market-aware footer with per-region links, brand lists, legal copy, and social icons
- **CLOTH**: `src/components/ProductCard.tsx` — prices auto-formatted to active market currency; condition labels in EN for UK
- **CLOTH**: `src/pages/ProductDetail.tsx` — market-aware: condition labels, trust items, form placeholders, phone regex patterns, CTA copy
- **CLOTH**: `src/pages/ProductList.tsx` — market-aware filter labels, pagination copy, API calls include `market` param
- **CLOTH**: `src/pages/Cart.tsx` — market-aware checkout form, currency display, empty states, phone validation
- **CLOTH**: `src/pages/Orders.tsx` — market-aware order list with status labels and locale date formatting
- **CLOTH**: `src/pages/Admin.tsx` — all API calls updated to include `market` param
- **CLOTH**: `src/api/client.ts` — all API methods now require `market: Market` as first arg; `displayPrice()` helper exported for cross-component use
- **CLOTH/api**: `src/models/store.ts` — added `market` field to products (UK/HK/CN/ALL); `filterProductsByMarket()` helper; 6 new UK-only + 3 new HK-only seed products added
- **CLOTH/api**: `src/models/types.ts` — added `MarketScope` type and optional `market` field to `Product` interface
- **CLOTH/api**: `src/routes/products.ts` — `GET /api/products` now reads `market` query param to filter by market scope
- **scrapers**: 5 new test files covering config, jobs, async_base, cache, metrics, and observability — 57 new tests (94 total, all passing)
- **scrapers**: `src/scrapers/async_base.py` — AsyncBaseScraper with semaphore concurrency, Prometheus metrics, exponential backoff
- **scrapers**: `src/metrics_app.py` — Prometheus ASGI mount for `/metrics` endpoint
- **scrapers**: `src/cache.py` — Redis-backed cache layer with graceful degradation (no-op on Redis unavailable)
- **scrapers**: `src/observability.py` — structlog + Sentry observability bootstrap
- **BuyerOS/admin**: 月結管理 page (`app/periods/page.tsx`) — period lifecycle management with open/close, SQL helpers, step-by-step guide
- **BuyerOS/admin**: 通訊記錄 page (`app/communications/page.tsx`) — communications CRM with channel/direction/tag filters, archive, new entry form
- **BuyerOS/admin**: Financials SVG P&L chart — 6-month revenue vs expenses bar chart
- **BuyerOS/admin**: Sidebar — added 運營 section with 通訊記錄 link; fixed `useRouter` import in `orders/new`
- **XAU/server**: Real price feed (`server/services/priceService.js`) — Finnhub primary → GoldAPI fallback → mock, EventEmitter polling, graceful SIGTERM shutdown

### Fixed
- **scrapers**: `dashboard.py` line 153 — `{port}` not interpolated in f-string (displayed literally instead of showing port number)
- **scrapers**: `config.py` — added `__getattr__` so `from src.config import settings` works (was only accessible via `get_settings()`)
- **scrapers**: `models/vinted.py` — `ItemCondition`, `ItemStatus`, `Gender` updated from deprecated `str, Enum` to `StrEnum`; added missing `Enum` import
- **scrapers**: `scrapers/aliexpress.py` — import sort order fixed (third-party `random` before first-party `src.config`)
- **scrapers**: auto-fixed 6 lint errors (unused imports in tests), updated `pyproject.toml` ruff config to modern `[tool.ruff.lint]` format, verified 37/37 tests pass and lint is clean
- **CLOTH**: fixed 3 TypeScript errors — `client.ts` Error.cause (ES2020 compat), `Home.tsx` PaginatedResponse unwrapping (`.data`), `ProductDetail.tsx` null guard in closure — type check clean ✅
- **CLOTH**: `ProductDetail.tsx` — added `if (!product) return` guard in `handleBuy` to prevent null access when product loads async

### Verified
- **scrapers**: CI tools verified — `ruff check` clean (0 warnings), `pytest` 94 passed (all modules, incl. new)
- **XAU**: demo server live at `http://localhost:4173/`, all 4 key pages confirmed 200 (index, obs-scene, live-engine, quiz, member-dashboard)
- **CLOTH**: project structure verified — all dirs present (api, web, scripts, agent-tasks, packages, services, apps), README complete and accurate

### Updated
- **BuyerOS**: `ARCHITECTURE.md` v1.1.1 — confirmed Deno runtime, Supabase Auth, Next.js admin UI, Edge Functions list; updated confirmation checklist

---

## [2026-05-23] — Day 3 — Schema Validation & Backup Hardening

### Added
- **BuyerOS**: `recon/supabase-audit.sql` — comprehensive DB audit script (12 diagnostic sections)
- **BuyerOS**: `recon/check-enums.sql` — validates `transactions.type` and `refunds.status` enum values against live schema
- **BuyerOS**: `recon/vps-recon.sh` — VPS environment reconnaissance and health check script
- **BuyerOS/backup-system**: Daily snapshot GitHub Actions workflow (`daily-backup.yml`)
- **BuyerOS/backup-system**: R2 storage backup GitHub Actions workflow (`storage-backup.yml`)
- **BuyerOS/backup-system**: `daily-snapshot.sh` — VPS snapshot automation script
- **BuyerOS/backup-system**: `health-check.sh` — backup integrity and VPS health monitor
- **BuyerOS/backup-system**: `restore-test.sh` — disaster recovery test harness
- **BuyerOS/backup-system**: `README.md` — implementation overview with file map and maintenance cycle
- **BuyerOS/backup-system**: `SETUP-PROGRESS.md` — step-by-step 6-phase 1.5h setup tracker
- **BuyerOS/backup-system**: `SECRETS-CHECKLIST.md` — secrets inventory and rotation checklist
- **BuyerOS**: `ARCHITECTURE.md` v1.1.0 — full system architecture documentation (tech stack, data model, 24 tables, deploy flow, security model)
- **BuyerOS**: `DEPLOY.md` — deployment runbook
- **BuyerOS**: `MIGRATION_APPLY_GUIDE.md` — step-by-step migration execution guide
- **BuyerOS**: `ROLLBACK_STRATEGY.md` — rollback procedures for each migration layer

### Changed
- **BuyerOS/seed.sql**: `journal_posting_rules` seed data confirmed present
- **BuyerOS/migrations**: Migration files reorganized with clear separation: `0001_initial_reconstructed.sql`, `0002_accounting_layer.sql`, `0002b_config_driven_posting.sql`, `0003_rls_and_audit.sql`

### Fixed
- **scrapers**: `import_exports.sh` — added improved logging, error handling, and safe symlink fallback

### Security
- **BuyerOS**: RLS and audit layer in `0003_rls_and_audit.sql` — all tables now have RLS enabled
- **BuyerOS**: `audit_log` table with automatic trigger-based entry creation
- **BuyerOS**: Secrets checklist (`SECRETS-CHECKLIST.md`) tracking all API keys and credentials

---

## [2026-05-22] — Day 2 — Cloud GPU Face Swap

### Added
- **cloud_gpu_faceswap**: Google Colab notebook — free tier GPU face swap workflow (`faceswap_free_colab.ipynb`)
- **cloud_gpu_faceswap**: Kaggle notebook — paid GPU face swap workflow (`faceswap_kaggle.ipynb`)
- **cloud_gpu_faceswap**: `faceswap_auto_colab.ipynb` — automated face swap pipeline for Colab
- **cloud_gpu_faceswap**: Shell script suite for local/server execution:
  - `scripts/00_make_upload_package.sh` — package creation
  - `scripts/01_setup_faceswap.sh` — environment setup
  - `scripts/02_prepare_workspace.sh` — workspace preparation
  - `scripts/03_extract_faces.sh` — face extraction
  - `scripts/04_train_preview.sh` — model training + preview
  - `scripts/05_convert_test.sh` — test conversion
  - `scripts/06_convert_full_if_approved.sh` — full conversion (gated)
- **cloud_gpu_faceswap**: Kaggle push bundle — `dataset/` and `kernel/` ready for Kaggle upload
- **cloud_gpu_faceswap**: `README.md`, `COLAB_FREE_README.md`, `KAGGLE_README.md` — platform-specific guides

---

## [2026-05-20] — Day 1 — AI Export Organizer & Linear Tracker

### Added
- **Claude Codex**: AI conversation export organizer (`import_exports.sh`) — structured imports for Claude, ChatGPT, Gemini, Perplexity, Other-AI
- **Claude Codex**: `detailed-conversation-organization-plan-zh.md` — Chinese-language export organization plan
- **Claude Codex**: Master summary system: `master-index.csv`, `master-summary.md`, `projects-overview.md`, `tags-reference.md`
- **Claude Codex**: Notion dashboard template (`notion-dashboard-template.md`)
- **Claude Codex**: Face fusion quick links (`facefusion-quick-links.html`)
- **Claude Artifacts**: Linear issue tracker (`linear-issue-tracker/index.html` + `thumbnail.png`)
- **XAU**: AI gold trading system business plan (`PLAN_CN.md`) — 10-section commercial plan with live-stream scripts, 6 ad variants, AI avatar strategy
- **XAU/docs**: GA4 analytics setup guide (`analytics-setup.md`) — custom event definitions, funnel setup
- **XAU/docs**: Changelog archive (`changes`) — GitHub releases page snapshot
- **_Organized**: GAP report template (`GAP-REPORT.md`)
- **_Organized**: Linear tracker standalone (`linear-tracker.html`) — 531-line issue tracker interface

---

## [2026-05-16] — Backup System v2026-05-16

### Added
- **BuyerOS/backup-system**: Initial backup system implementation
  - `backup-system/` directory with scripts and workflows
  - Daily backup GitHub Actions pipeline
  - VPS snapshot automation
  - Restore test procedures
  - Secrets management checklist

---

## [v1.0.0] — 2026-05-16 — Workspace Initialization

### Added
- Initial workspace structure under `_Organized/Claude/Claude/Projects/買手對象系統/`
- Initial migration files under `supabase/migrations/`
- Initial Edge Functions under `supabase/functions/`
- Initial Admin UI scaffold under `apps/admin/`
- `package.json` and monorepo root configuration
- `.gitignore` and workspace configuration files

---

## Project Status Overview

| Project | Status | Next Milestone |
|---------|--------|---------------|
| **scrapers** | Active development | Test CI/CD pipelines, add more scrapers |
| **BuyerOS** | P1: Schema validation pending | Run `recon/supabase-audit.sql` in Supabase Studio |
| **cloud_gpu_faceswap** | Complete — ready to deploy | Push to Kaggle, run Colab workflows |
| **XAU Gold Trading** | Phase 1 demo planning | Build demo with mock data |
| **CLOTH** | POC — features defined | Implement platform connectors |

---

*Last updated: 2026-05-23*
