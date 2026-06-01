# BuyerOS Improvement Roadmap

**Repository:** `/Users/rubykan/Downloads/buyeros-production-repo-v8`  
**Analysis Date:** June 1, 2026  
**Codebase Size:** 84 Python files (backend), 8 TypeScript files (frontend)

---

## Executive Summary

The BuyerOS codebase is a FastAPI backend with Next.js frontend for a luxury resale platform, featuring AI-powered agents (Ops, Finance, Supervisor), multi-bank reconciliation, Shopify/TikTok integrations, Telegram webhooks, and comprehensive smoke testing.

**Overall Assessment:** The architecture is well-designed with good separation of concerns, but critical security vulnerabilities exist, the frontend is architecturally immature, and infrastructure lacks offsite backups and disaster recovery. The codebase needs security hardening before it can be considered production-ready at scale.

---

## 1. CRITICAL (Must Fix) — Production Breaking Issues

### 1.1 Hardcoded Secrets Committed to Git History

| Attribute | Value |
|-----------|-------|
| **Severity** | CRITICAL |
| **Files** | `.env` (committed), `.env.production.local`, `.env.staging.local` |
| **Effort** | Medium |
| **Description** | Production secrets (API keys, Supabase credentials, Telegram tokens, admin tokens) committed to repository. The `.env` file at root contains `BUYEROS_API_KEY`, `ADMIN_DASHBOARD_TOKEN`, `OPENROUTER_API_KEY`, `SUPABASE_KEY`, and `TELEGRAM_BOT_TOKEN`. All must be rotated. |

**Remediation:**
1. Rotate all secrets immediately — treat `.env` contents as compromised
2. Verify `.env` is in `.gitignore` and remove from git history (`git filter-branch` or BFG)
3. Implement `.env.example` as the only committed template
4. Add pre-commit hook to prevent `.env` commits

---

### 1.2 Weak Admin Dashboard Token

| Attribute | Value |
|-----------|-------|
| **Severity** | CRITICAL |
| **Files** | `.env` (`ADMIN_DASHBOARD_TOKEN=hffffjybhbkjj`) |
| **Effort** | Small |
| **Description** | The admin dashboard token `hffffjybhbkjj` follows a trivial pattern (`h` + repeated character). Combined with its presence in the committed `.env`, this is effectively a public credential. |

**Remediation:**
1. Generate 32+ character cryptographically random token: `openssl rand -hex 32`
2. Move to secret manager (Vault, AWS Secrets Manager, Doppler)
3. Add rate limiting to admin endpoints
4. Add audit logging for admin dashboard access

---

### 1.3 Triple-Competing Auth Implementations with Dev Bypass

| Attribute | Value |
|-----------|-------|
| **Severity** | CRITICAL |
| **Files** | `backend/app/auth.py`, `backend/app/dependencies.py`, `backend/app/security.py` |
| **Effort** | Medium |
| **Description** | Three separate auth implementations exist with conflicting behavior: `auth.py` uses `BUYEROS_API_KEY`, `dependencies.py` uses `SHOPIFY_API_KEY`, and `security.py` supports both Bearer and X-API-Key. All three fall through to allowing requests in dev mode when no key is configured. |

**Remediation:**
1. Consolidate into single auth module (keep `auth.py`, deprecate the other two)
2. Add `BUYEROS_ENV=production` flag that **requires** `BUYEROS_API_KEY` to be set
3. Fail FastAPI startup if auth is misconfigured in production mode
4. Audit every router's auth dependency

---

### 1.4 Unauthenticated WebSocket Endpoint

| Attribute | Value |
|-----------|-------|
| **Severity** | CRITICAL |
| **Files** | `backend/app/orchestration.py:188-206` |
| **Effort** | Small |
| **Description** | `WS /ws/trace/{trace_id}` accepts connections without authentication. Any client can subscribe to any trace ID, potentially viewing sensitive agent state and memory contents. |

**Remediation:**
1. Add token validation via query param (`?token=xxx`) or subprotocol handshake
2. Validate `trace_id` belongs to the authenticated user
3. Add connection logging for audit trail
4. Consider WebSocket-specific rate limiting

---

### 1.5 CORS Configuration Allows Production IP + Localhost

| Attribute | Value |
|-----------|-------|
| **Severity** | CRITICAL |
| **Files** | `backend/app/main.py:58-68` |
| **Effort** | Small |
| **Description** | CORS allows `http://206.189.116.155:3000` (a specific VPS IP) alongside localhost. This IP address should be a DNS name, not hardcoded. No environment-based CORS configuration. |

**Remediation:**
1. Use `BUYEROS_CORS_ORIGINS` env var for all origins
2. Replace hardcoded IP with `buyeros.app` domain
3. Remove localhost from production builds (only allow in non-production env)
4. Add CORS validation to smoke tests

---

## 2. HIGH PRIORITY — Security & Architecture

### 2.1 Missing Rate Limiting on All Endpoints

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | All router files |
| **Effort** | Medium |
| **Description** | No rate limiting exists on any API endpoint. Combined with the auth bypass issues, this enables API key brute forcing, DoS attacks, and cost exhaustion on OpenRouter AI calls. |

**Remediation:**
1. Add SlowAPI for FastAPI rate limiting
2. Configure tiered limits: 100/min general, 10/min for AI endpoints, 5/min for task dispatch
3. Use Redis-backed rate limiter for distributed deployments
4. Return `Retry-After` headers on 429 responses

---

### 2.2 Insecure UUID Generation for Transaction IDs

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `backend/app/services/bank_import_service.py:147,226`, `backend/app/services/recon_store.py` |
| **Effort** | Small |
| **Description** | `uuid.uuid4()` is not cryptographically secure. Transaction IDs, statement IDs, and recon IDs use predictable random UUIDs that could theoretically be enumerated. |

**Remediation:**
```python
import secrets
secure_id = f"tx-{secrets.token_hex(12)}"
```
Replace all `uuid.uuid4().hex[:12]` patterns with `secrets.token_hex(12)`.

---

### 2.3 MemoryStore Silently Drops Audit-Critical Data

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `backend/app/memory_store.py:44-48` |
| **Effort** | Small |
| **Description** | Supabase write failures are caught with bare `except Exception: pass`. Audit logs, agent memory, and task state can be silently lost without any alerting. |

```python
try:
    self._save_supabase(item)
except Exception:
    pass  # Tests and local smoke should keep working
```

**Remediation:**
1. Log at WARNING level minimum: `logger.warning("Supabase write failed: %s", exc)`
2. Increment error counter metric
3. Implement retry with exponential backoff (3 attempts)
4. Fall back to local storage if Supabase is down, not silent discard

---

### 2.4 Service Instantiation Per HTTP Request

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `backend/app/routers/api.py:46-47`, `bank_import_service.py`, `recon_store.py` |
| **Effort** | Medium |
| **Description** | Every route handler creates a new service instance (`ExpenseService()`, `BankImportService()`, etc.). This means new SQLite connections per request, no shared state, and **no testability** via dependency injection. |

```python
# api.py:46-47 — creates new service on every call
async def list_expenses(...):
    from app.services.expense_service import ExpenseService
    service = ExpenseService()  # New instance per request!
```

**Remediation:**
1. Create application-level singleton services in `main.py`
2. Use FastAPI `Depends()` for request-level services
3. Add proper dependency injection container
4. Mock services in tests via fixture injection

---

### 2.5 Missing Transaction Isolation in Bank Import

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `backend/app/services/bank_import_service.py:222-248` |
| **Effort** | Small |
| **Description** | `bank_statements` insert and `bank_transactions` inserts are separate operations. If the transaction inserts fail (e.g., due to a row error), you have orphaned statement records with no transactions. |

**Remediation:**
```python
# Use Supabase's RPC or edge function for atomic multi-table inserts
# Or use a transaction wrapper if available
```

---

### 2.6 Synchronous `requests` in Async Event Loop

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `backend/app/ai_router.py:87-104`, `backend/app/services/receipt_vision_service.py:156-165`, `backend/app/services/finance_service.py:44-49`, `backend/app/services/finance_sheets.py:78` |
| **Effort** | Medium |
| **Description** | Using synchronous `requests.post()` inside FastAPI `async def` handlers blocks the event loop. Under load, this causes thread starvation and degraded throughput. |

```python
# ai_router.py:87 — BLOCKS the event loop
async def route(...):
    response = requests.post(...)  # Synchronous!
```

**Remediation:**
1. Replace all `requests` with `httpx.AsyncClient`
2. Use a shared client instance with connection pooling
3. Add async timeout configuration

---

### 2.7 No Route Protection Middleware on Frontend

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `frontend/` |
| **Effort** | Medium |
| **Description** | The frontend has NextAuth configured but **no `middleware.ts`** to protect routes. All pages (`/`, `/expenses`) are accessible without authentication. The API proxy has no auth check either. |

**Remediation:**
1. Add `middleware.ts` that validates session on all routes except `/auth/*`
2. Add auth check to the API proxy route
3. Add redirect to `/auth/signin` for unauthenticated users

---

### 2.8 Monolithic Frontend Page Components

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Files** | `frontend/app/page.tsx` (~1700 lines), `frontend/app/expenses/page.tsx` (~490 lines) |
| **Effort** | Large |
| **Description** | Two oversized client components contain all UI logic. This makes the code untestable, unmaintainable, and prevents code reuse. Dead components exist in `common/` and `dashboard/` that are never imported. |

**Remediation:**
1. Extract into 20-30 focused components: `TaskCard`, `SubtaskList`, `TimelineView`, `TeamStatusCard`, `ActionButton`, `ResultPanel`, etc.
2. Implement proper state management (React Query/TanStack Query for server state, Zustand for UI state)
3. Remove dead code from `common/` and `dashboard/`

---

## 3. MEDIUM PRIORITY — Quality & Maintainability

### 3.1 Missing Input Validation — Dict[str, Any] Endpoints

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `backend/app/routers/api.py` — all endpoints accepting `Dict[str, Any]` |
| **Effort** | Medium |
| **Description** | Endpoints like `create_expense(data: Dict[str, Any])`, `import_bank_transactions(data: Dict[str, Any])`, and `dispatch_task(data: Dict[str, Any])` bypass Pydantic validation entirely. Type safety is lost at the API boundary. |

**Remediation:**
1. Replace all `Dict[str, Any]` with proper Pydantic models
2. Add request/response models for each endpoint
3. Enable FastAPI's auto-generated OpenAPI docs with examples

---

### 3.2 Silent Failure Pattern in Bank Import Service

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `backend/app/services/bank_import_service.py:180-182` |
| **Effort** | Small |
| **Description** | Idempotency check silently catches exceptions and proceeds with insert. Schema/table issues are hidden. |

```python
except Exception:
    pass  # If schema/table doesn't support query yet, proceed with insert
```

**Remediation:**
1. Log the exception
2. Add a feature flag to distinguish "schema not ready" from actual errors
3. Validate schema at startup, not per-request

---

### 3.3 No Health Checks for Downstream Dependencies

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `backend/app/main.py:75-77` |
| **Effort** | Small |
| **Description** | `/health` returns static `{"status": "healthy"}` without checking Redis, Supabase, or OpenRouter connectivity. Kubernetes/load balancers get false positives. |

**Remediation:**
1. Add `/health/live` (always returns 200 if process is up)
2. Add `/health/ready` (checks Redis ping, Supabase query, OpenRouter status)
3. Return degraded status with component-level details:
```json
{"status": "degraded", "redis": "ok", "supabase": "ok", "openrouter": "unavailable"}
```

---

### 3.4 No Request ID / Correlation ID Propagation

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `backend/app/trace.py`, all routers |
| **Effort** | Small |
| **Description** | `trace.py` has `ContextVar` for trace context but it's not automatically populated from `X-Request-ID` headers. Logs from different requests cannot be correlated in production. |

**Remediation:**
1. Add middleware to extract or generate `X-Request-ID`
2. Inject into trace context on every request
3. Include in all log entries
4. Return `X-Request-ID` in response headers

---

### 3.5 Duplicate Supabase Client Patterns

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `memory_store.py`, `recon_store.py`, `bank_import_service.py` |
| **Effort** | Medium |
| **Description** | Three different patterns for Supabase: `MemoryStore` uses raw `httpx` POST to REST API, while `ReconStore` and `BankImportService` use the Python client. Inconsistent, hard to test, multiple connection pools. |

**Remediation:**
1. Standardize on Supabase Python client everywhere
2. Create shared `get_supabase_client()` factory function
3. Configure connection pooling once

---

### 3.6 Frontend: API Key in localStorage

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `frontend/app/page.tsx` |
| **Effort** | Small |
| **Description** | The `BUYEROS_API_KEY` is stored in `localStorage` under `buyeros.api.key`. This is vulnerable to XSS attacks. The key should only ever live server-side (which the proxy does correctly), not in the browser. |

**Remediation:**
1. Remove `buyeros.api.key` from localStorage
2. Pass API key server-side only via the Next.js proxy (already implemented correctly)
3. Remove UI controls that save API key to localStorage

---

### 3.7 Frontend: Global Loading State Blocks Entire UI

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `frontend/app/page.tsx` |
| **Effort** | Small |
| **Description** | Single `loading: boolean` state disables the entire UI during any async operation. Users cannot switch tabs, view results of previous operations, or take concurrent actions. |

**Remediation:**
1. Add per-operation loading states using React Query's `isLoading`
2. Show inline spinners on specific action buttons
3. Enable concurrent operations

---

### 3.8 Frontend: Incompatible CSS in globals.css

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `frontend/app/globals.css` |
| **Effort** | Small |
| **Description** | Uses `color-mix(in oklch, ...)` and `oklch()` color syntax which requires Safari 16.4+ and Firefox 113+. Users on older browsers will see broken colors. |

**Remediation:**
1. Provide fallback colors using traditional `rgb()` or `hsl()` before `color-mix()`
2. Use `@supports (color: color-mix(in oklch, red, blue))` feature query
3. Test on Safari 15, Firefox 100, Chrome 100 minimums

---

### 3.9 Duplicate Registry Patterns

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `backend/app/registry.py`, `backend/app/context/provider_registry.py` |
| **Effort** | Medium |
| **Description** | Two registry patterns exist: simple `AgentRegistry`/`ToolRegistry` in `registry.py` and sophisticated `ProviderRegistry` with fallback chains in `context/`. The old registry is likely dead code. |

**Remediation:**
1. Audit usage of `registry.py` across codebase
2. Migrate to `ProviderRegistry` if unused
3. Add integration tests for registry operations

---

### 3.10 Frontend: Dead UI Components

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `frontend/components/common/Button.tsx`, `Card.tsx`, `dashboard/StatusCard.tsx`, `ApiConfig.tsx` |
| **Effort** | Small |
| **Description** | Components are defined but never imported anywhere. Code bloat with no test coverage. |

**Remediation:**
1. Remove dead components or add tests
2. Set up ESLint rule to warn on unused exports
3. Add import assertion for component files

---

## 4. LOW PRIORITY — Future Improvements

### 4.1 No Offsite Backup — Backups Stored on VPS

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `infra/backup_vps.sh` |
| **Effort** | Medium |
| **Description** | `backup_vps.sh` stores backups in `/opt/buyeros-backups/` on the same VPS. A VPS failure/loss means no backups. No S3/GCS/Azure Blob offsite storage. |

**Remediation:**
1. Add S3/GCS upload step to backup script
2. Configure cross-region replication
3. Add backup verification (automated restore test)

---

### 4.2 No Terraform / Infrastructure as Code

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `infra/` |
| **Effort** | Large |
| **Description** | Infrastructure is managed manually via DigitalOcean console. No Terraform, CloudFormation, or Pulumi. VPS sizing, networking, and firewall rules are not codified. |

**Remediation:**
1. Create Terraform modules for VPS, firewall rules, DNS
2. State file stored in S3 with DynamoDB locking
3. Separate staging and production workspaces

---

### 4.3 No Automated Failover

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `infra/failover_smoke.sh`, `infra/deploy_vps.sh` |
| **Effort** | Medium |
| **Description** | Both VPSes on the same provider (DigitalOcean). Failover requires manual DNS change. No health-check-based automatic failover. |

**Remediation:**
1. Set up DNS failover with health checks (Route 53, Cloudflare)
2. Consider multi-cloud deployment for true DR
3. Document RTO/RPO targets

---

### 4.4 LinkedIn Scraper Relies on Google Search

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `scrapers/linkedin_scraper.py` |
| **Effort** | Medium |
| **Description** | LinkedIn profile discovery uses Google search, which violates Google's ToS. Success rate is likely low and may trigger Google rate limiting. |

**Remediation:**
1. Use LinkedIn's official API or Sales Navigator API
2. Or remove Google search dependency entirely
3. Add clear comments about ToS compliance

---

### 4.5 Basic Browser Stealth — Easily Detected

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `scrapers/browser_scraper.py` |
| **Effort** | Medium |
| **Description** | Playwright stealth only hides `navigator.webdriver`. Does not mask automation signals like canvas fingerprints, audio context, or WebGL renderer differences. Advanced anti-bot systems (Distil, DataDome, Cloudflare Bot Management) will detect. |

**Remediation:**
1. Add `stealth` npm package for Playwright
2. Consider dedicated scraping APIs (ScrapingBee, SmartProxy, Bright Data)
3. Implement CAPTCHA handling

---

### 4.6 CI: Type Checking Errors Silently Ignored

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `scrapers/.github/workflows/ci.yml` |
| **Effort** | Small |
| **Description** | `mypy --ignore-missing-imports --no-error-summary || true` masks type errors. CI passes even when mypy reports errors. |

**Remediation:**
1. Remove `|| true` from mypy step
2. Use strict mode: `mypy --strict`
3. Set `mypy` version in requirements.txt

---

### 4.7 No Database Migrations System

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `backend/app/services/expense_service.py` |
| **Effort** | Medium |
| **Description** | SQLite tables created via `CREATE TABLE IF NOT EXISTS` in service init. No Alembic or similar for schema versioning. Schema changes require manual coordination. |

**Remediation:**
1. Add Alembic for SQLite migrations
2. Version all schema changes
3. Add migration testing in CI

---

### 4.8 Missing OpenAPI Documentation

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | All routers |
| **Effort** | Medium |
| **Description** | Minimal docstrings on endpoints. FastAPI auto-generated `/docs` will be sparse. |

**Remediation:**
1. Add docstrings to all endpoints
2. Document request/response schemas
3. Add OpenAPI `examples` for each endpoint

---

### 4.9 Circuit Breaker Is Global, Not Per-Role

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `backend/app/ai_router.py:22-58` |
| **Effort** | Small |
| **Description** | Single circuit breaker for all AI routing. If one role's model fails 5 times, all roles are blocked even if their models are healthy. |

**Remediation:**
1. Implement per-role circuit breakers: `_circuits: Dict[str, CircuitBreaker]`
2. Persist state in Redis for distributed deployments

---

### 4.10 No OpenTelemetry Tracing

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `backend/app/trace.py` |
| **Effort** | Medium |
| **Description** | Custom trace context exists but no OpenTelemetry integration for distributed tracing across services. |

**Remediation:**
1. Add `opentelemetry-sdk` and `opentelemetry-instrumentation-fastapi`
2. Instrument all HTTP calls and database queries
3. Export traces to Jaeger or Tempo

---

## 5. FRONTEND-SPECIFIC ISSUES

### 5.1 No Form Library — Manual Validation

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `frontend/app/page.tsx`, `expenses/page.tsx` |
| **Effort** | Medium |
| **Description** | No react-hook-form, zod, or similar. Form state managed manually with `useState`. Easy to introduce validation bugs. |

**Remediation:**
1. Add react-hook-form with zod validation
2. Define schemas for all forms
3. Show inline validation errors

---

### 5.2 No React Query / TanStack Query

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Files** | `frontend/` |
| **Effort** | Large |
| **Description** | Manual `fetch` calls with `useEffect` for data fetching. No caching, no background refetch, no optimistic updates, no loading/error states per query. |

**Remediation:**
1. Add TanStack Query
2. Replace all data fetching with typed queries
3. Add query invalidation after mutations

---

### 5.3 No i18n — Hardcoded Chinese Text

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `frontend/app/page.tsx`, `expenses/page.tsx` |
| **Effort** | Medium |
| **Description** | All UI text is hardcoded in Chinese (Traditional). No i18n system for localization. |

**Remediation:**
1. Add next-intl or react-intl
2. Extract all strings to translation files
3. Support `en`, `zh-Hant` locales

---

### 5.4 ESLint: Multiple `eslint-disable` Comments

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Files** | `frontend/app/page.tsx` |
| **Effort** | Small |
| **Description** | Multiple `// eslint-disable-next-line react-hooks/exhaustive-deps` comments. Risk of stale closure bugs when dependencies change. |

**Remediation:**
1. Audit each eslint-disable and address the root cause
2. Use `useMemo` / `useCallback` properly to avoid the warning
3. Add ESLint rule to fail on new eslint-disable additions

---

## Sprint Recommendations

### Sprint 1 (1-2 weeks): Security Hardening
1. Rotate all secrets (Critical 1.1, 1.2)
2. Consolidate auth into single module, remove dev bypass (Critical 1.3)
3. Add auth to WebSocket endpoint (Critical 1.4)
4. Lock CORS via environment config (Critical 1.5)
5. Add rate limiting (High 2.1)
6. Add route protection middleware (High 2.7)

### Sprint 2 (1-2 weeks): Data Integrity & Reliability
1. Replace `uuid.uuid4` with `secrets.token_hex` (High 2.2)
2. Fix MemoryStore silent failures (High 2.3)
3. Add proper dependency injection for services (High 2.4)
4. Wrap bank imports in transactions (High 2.5)
5. Replace sync `requests` with async `httpx` (High 2.6)
6. Add per-endpoint health checks (Medium 3.3)

### Sprint 3 (2-3 weeks): Frontend Architecture
1. Decompose `page.tsx` into 20+ components (High 2.8)
2. Remove dead components (Medium 3.10)
3. Remove API key from localStorage (Medium 3.6)
4. Replace global loading with per-operation states (Medium 3.7)
5. Fix CSS compatibility (Medium 3.8)
6. Add TanStack Query (Medium 5.2)
7. Add form validation with react-hook-form (Medium 5.1)

### Sprint 4 (2 weeks): Testing & Observability
1. Add request ID propagation middleware (Medium 3.4)
2. Replace `Dict[str, Any]` with Pydantic models (Medium 3.1)
3. Standardize Supabase client (Medium 3.5)
4. Add Alembic migrations (Low 4.7)
5. Add OpenTelemetry tracing (Low 4.10)
6. Fix CI mypy mask (Low 4.6)

### Sprint 5+ (Ongoing): Infrastructure & Polish
1. Add offsite backup to S3 (Low 4.1)
2. Implement Terraform IaC (Low 4.2)
3. Set up DNS failover (Low 4.3)
4. Add OpenAPI documentation (Low 4.8)
5. Implement per-role circuit breakers (Low 4.9)
6. Add i18n support (Low 5.3)

---

## Appendix A: File Analysis Summary

### Backend (84 Python files)

| Category | Count | Notes |
|----------|-------|-------|
| Routers | 4 | api, shopify, tiktok, telegram (broken import) |
| Services | 30+ | Good separation of concerns |
| Agents | 2 | OpsAgent, FinanceAgent; Supervisor orchestrator |
| Context Adapters | 9 | Claude, OpenAI, Gemini, DeepSeek, Grok, etc. |
| Bank Parsers | 3 | HSBC HK, Generic CSV, + base |
| Tests | 20+ | Good coverage of core services |
| Schemas | 30+ | Pydantic models for requests/responses |

### Frontend (8 TypeScript files)

| Category | Count | Notes |
|----------|-------|-------|
| Pages | 4 | main dashboard, expenses, auth pages |
| API Routes | 2 | buyeros proxy, nextauth |
| Components | 3 | ErrorBoundary, SessionProvider, DebugPanel |
| Dead Components | 5+ | Button, Card, StatusCard, ApiConfig (never used) |

### Infrastructure

| Category | Files | Notes |
|----------|-------|-------|
| Deployment | 5 | deploy, rollback, smoke, preflight, restart |
| Backup/Restore | 2 | backup_vps, restore_test |
| Smoke Tests | 10+ | Comprehensive API, UI, 4-system, Telegram smoke tests |
| Migrations | 1 | SQL migrations directory |

### Scraper Architecture

| Category | Notes |
|----------|-------|
| Base Classes | `BaseScraper` (sync/requests), `AsyncBaseScraper` (async/httpx) |
| Site Scrapers | Amazon, eBay, AliExpress, Tesco, Google Shopping, LinkedIn, Nike |
| B2B Scrapers | Apollo.io, Hunter.io, Companies House UK |
| Adapters | Base, Custom REST, Shopify, Stripe, PayPal |
| CI | GitHub Actions (CI, scheduled runs, label-based) |

---

## Appendix B: Architecture Scores

| Layer | Score | Key Strengths | Key Weaknesses |
|-------|-------|---------------|----------------|
| **Backend API** | 7/10 | Layered services, registry patterns, circuit breaker, fallback chains | Sync HTTP in async context, Dict[str, Any] endpoints, service-per-request |
| **AI Routing** | 7/10 | Provider registry with fallback, circuit breaker, per-role routing | Global circuit breaker, keyword-based routing is brittle |
| **Data Layer** | 6/10 | Multi-backend (SQLite, Supabase, Redis), in-memory fallback | Silent failures, no transactions, duplicate client patterns |
| **Frontend** | 4/10 | NextAuth configured, API proxy pattern | Monolithic components, no state management, no route protection |
| **Security** | 3/10 | Auth exists, non-root Docker | Dev bypass, unauth WebSocket, no rate limiting, secrets in git |
| **Infrastructure** | 5/10 | Release versioning, smoke tests, WAL SQLite | No IaC, local-only backups, no automated failover |
| **Scrapers** | 6/10 | Pydantic models, rate limiting, retry logic | Basic stealth, Google ToS risk, Loyalty scraper has `input()` passwords |
| **Observability** | 6/10 | Trace context, JSON logging, circuit breaker status | No OpenTelemetry, no structured metrics, no correlation IDs |

---

## Appendix C: Quick Wins (Under 30 Minutes)

1. **Remove `|| true` from mypy in CI** — just delete `|| true` from the workflow
2. **Generate secure admin token** — `openssl rand -hex 32`
3. **Add logging to MemoryStore** — change `except Exception: pass` to `logger.warning(...)`
4. **Add WebSocket auth** — validate token in `query_params` on connect
5. **Remove dead components** — delete files in `common/` and `dashboard/` that are never imported
6. **Fix CSS fallback** — add `rgb()` fallback before `color-mix()` in globals.css
7. **Replace `uuid.uuid4` with `secrets`** — one import change, affects 3 files
8. **Add request ID middleware** — ~10 lines in `main.py`
