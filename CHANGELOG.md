# Changelog

All notable changes to this workspace are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **scrapers**: Full multi-platform scraping CLI scaffold with 7 platform scrapers (LinkedIn, B2B Contact Finder, Trip.com, Amazon, eBay, Loyalty Checker, UK Supermarket)
- **scrapers**: `config.yaml` for centralized configuration management
- **scrapers**: Docker + Docker Compose setup with multi-stage Dockerfile
- **scrapers**: `pyproject.toml` with Click, Pydantic, Rich, and pytest
- **scrapers**: GitHub Actions CI workflow (`ci.yml`) and scheduled run workflow (`scheduled.yml`)
- **scrapers**: Makefile with `install`, `test`, `lint`, `docker-build`, `docker-run` targets
- **scrapers**: `import_exports.sh` — AI conversation export organizer (Claude, ChatGPT, Gemini, Perplexity, Other-AI)
- **scrapers**: Standalone scraper scripts (`amazon_scraper.py`, `ebay_scraper.py`, `linkedin_scraper.py`, `loyalty_checker.py`, `trip_scraper.py`, `uk_supermarket_scraper.py`, `b2b_contact_finder.py`)

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
