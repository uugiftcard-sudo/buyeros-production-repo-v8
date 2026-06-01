# BuyerOS Improvement Roadmap

**Repository:** `/Users/rubykan/Downloads/buyeros-production-repo-v8`  
**Analysis Date:** June 1, 2026  
**Codebase Size:** 84 Python files (backend), 8 TypeScript files (frontend)

---

## Executive Summary

The BuyerOS codebase is a production-ready FastAPI backend with Next.js frontend for a luxury resale platform. It features AI-powered agents (Ops, Finance, Supervisor), multi-bank reconciliation, Shopify/TikTok integrations, and Telegram webhook support.

**Overall Assessment:** The architecture is sound with good separation of concerns, but there are critical security vulnerabilities, missing test coverage, and architectural debt that should be addressed before scaling.

---

## 1. CRITICAL (Must Fix) — Production Breaking Issues

### 1.1 Hardcoded Secrets in .env Exposed in Git History

**Severity:** CRITICAL  
**Files:** `.env` (committed to repo), `backend/app/main.py`  
**Estimated Effort:** Medium  
**Description:**  
The `.env` file containing production secrets (API keys, Supabase credentials, Telegram tokens) was committed to the repository. These secrets now exist in git history and should be considered compromised.

**Remediation:**
1. Immediately rotate all secrets in `.env`
2. Add `.env` to `.gitignore` (it already appears to be, but verify)
3. Use `.env.example` as template only
4. Implement secret rotation procedure

### 1.2 Weak Admin Dashboard Token

**Severity:** CRITICAL  
**Files:** `.env` (`ADMIN_DASHBOARD_TOKEN=hffffjybhbkjj`)  
**Estimated Effort:** Small  
**Description:**  
The admin dashboard token `hffffjybhbkjj` is trivially guessable (simple pattern). Anyone with access to the repository can access the admin dashboard.

**Remediation:**
1. Generate cryptographically secure random token (32+ chars)
2. Store in secure secret management (Vault, AWS Secrets Manager)
3. Add rate limiting to admin endpoints

### 1.3 API Key Validation Bypass

**Severity:** CRITICAL  
**Files:** `backend/app/auth.py`, `backend/app/dependencies.py`  
**Estimated Effort:** Medium  
**Description:**  
Two separate auth mechanisms exist with different behaviors:
- `auth.py:verify_api_key()` allows all requests when `BUYEROS_API_KEY` is not set (dev mode)
- `dependencies.py:verify_api_key()` allows all requests when `SHOPIFY_API_KEY` is not set

The frontend proxy (`frontend/app/api/buyeros/[...path]/route.ts`) reads API keys from environment files and passes them server-side, but downstream routers may use different verification.

**Remediation:**
1. Consolidate auth logic into single module
2. Add `PRODUCTION_API_KEY` env var that must be set for production
3. Fail fast if neither key is configured in production mode

### 1.4 CORS Allows All Origins When Key Not Set

**Severity:** CRITICAL  
**Files:** `backend/app/main.py:58-68`  
**Estimated Effort:** Small  
**Description:**  
CORS allows `http://206.189.116.155:3000` (production IP) and localhost. If auth is bypassed (see 1.3), this endpoint is accessible from browsers.

**Remediation:**
1. Lock CORS to production domain only
2. Use environment-based configuration
3. Remove localhost from production builds

### 1.5 Weak Fallback Authentication in Bearer Token Verification

**Severity:** CRITICAL  
**Files:** `backend/app/auth.py:43-62`  
**Estimated Effort:** Small  
**Description:**  
`verify_bearer_token()` returns `"anonymous"` when no credentials provided. This allows unauthenticated access when Bearer token auth is expected. The function is used in `optional_auth()` which falls through to anonymous mode.

**Remediation:**
1. Require authentication by default, make anonymous opt-in
2. Add proper JWT validation with expiration
3. Audit all endpoints using `optional_auth`

---

## 2. HIGH PRIORITY — Security & Architecture

### 2.1 Missing Rate Limiting on All Endpoints

**Severity:** HIGH  
**Files:** All router files (`backend/app/routers/*.py`)  
**Estimated Effort:** Medium  
**Description:**  
No rate limiting exists on any API endpoint. This enables:
- API key brute forcing
- Denial of service
- Cost exhaustion on AI model calls

**Remediation:**
1. Add SlowAPI for FastAPI rate limiting
2. Configure per-endpoint limits (e.g., 100/min general, 10/min for AI calls)
3. Add Redis-backed distributed rate limiting

### 2.2 Insecure Random for UUID Generation

**Severity:** HIGH  
**Files:** `backend/app/services/bank_import_service.py:147,226`, `backend/app/services/recon_store.py`  
**Estimated Effort:** Small  
**Description:**  
Uses `uuid.uuid4()` which is not cryptographically secure for IDs that could be guessed. Transaction IDs and statement IDs should use secure generation.

**Remediation:**
```python
import secrets
secure_id = f"tx-{secrets.token_hex(12)}"
```

### 2.3 MemoryStore Silently Swallows Errors

**Severity:** HIGH  
**Files:** `backend/app/memory_store.py:44-48`  
**Estimated Effort:** Small  
**Description:**  
```python
try:
    self._save_supabase(item)
except Exception:
    pass  # Tests and local smoke should keep working
```
This silently drops audit-critical data without alerting.

**Remediation:**
1. Log failures at WARNING level minimum
2. Add metrics for Supabase write failures
3. Implement retry with exponential backoff

### 2.4 Duplicate Agent Registries

**Severity:** MEDIUM  
**Files:** `backend/app/registry.py`, `backend/app/context/provider_registry.py`  
**Estimated Effort:** Medium  
**Description:**  
Two separate registry patterns exist:
- `AgentRegistry`/`ToolRegistry` in `registry.py` — simple dict-based
- `ProviderRegistry` in `context/provider_registry.py` — more sophisticated

This creates confusion about which to use and may lead to dead code.

**Remediation:**
1. Deprecate `registry.py` in favor of `context/provider_registry.py`
2. Migrate all registrations
3. Add integration tests for registry operations

### 2.5 Missing Input Validation on Expense Service

**Severity:** MEDIUM  
**Files:** `backend/app/services/expense_service.py`  
**Estimated Effort:** Small  
**Description:**  
`ExpenseService` validates amounts in `submit()` but doesn't validate:
- `buyer_name` length or character restrictions
- `description` for injection attacks
- `category` against VALID_CATEGORIES in some code paths

**Remediation:**
1. Add comprehensive Pydantic validation
2. Sanitize all string inputs
3. Add parameterized queries (already using them correctly)

### 2.6 Missing Transaction Isolation in Bank Import

**Severity:** HIGH  
**Files:** `backend/app/services/bank_import_service.py:222-248`  
**Estimated Effort:** Small  
**Description:**  
Statement insert and transaction inserts are not wrapped in a transaction. If transaction inserts fail, you have orphaned statement records.

**Remediation:**
```python
with self.supabase.transaction() as tx:
    tx.table("bank_statements").insert(statement_payload).execute()
    tx.table("bank_transactions").insert(tx_rows).execute()
```

### 2.7 Frontend Only Has 8 Source Files

**Severity:** MEDIUM  
**Files:** `frontend/app/`  
**Estimated Effort:** Large  
**Description:**  
The frontend appears minimal with only 8 source files (excluding node_modules). Key components may be missing:
- Error handling UI
- Loading states
- Mobile responsiveness
- Data fetching patterns

**Remediation:**
1. Audit frontend completeness
2. Add proper error boundaries (see `ErrorBoundary` import in `layout.tsx`)
3. Implement proper loading states

---

## 3. MEDIUM PRIORITY — Quality & Maintainability

### 3.1 Incomplete Test Coverage

**Severity:** MEDIUM  
**Files:** `backend/tests/`  
**Estimated Effort:** Medium  
**Description:**  
While 20+ test files exist, coverage is likely incomplete for:
- `ai_router.py` — no dedicated test file
- `orchestration.py` — critical WebSocket/path but minimal tests
- `supervisor.py` — routing logic needs edge case coverage

**Remediation:**
1. Add integration tests for AI router with mock OpenRouter
2. Test WebSocket connections and disconnections
3. Add property-based tests for bank import parsing

### 3.2 Using Synchronous `requests` in Async Context

**Severity:** MEDIUM  
**Files:** `backend/app/ai_router.py:87-104`, `backend/app/services/receipt_vision_service.py:156-165`  
**Estimated Effort:** Medium  
**Description:**  
```python
async def route(...):
    response = requests.post(...)  # Blocks event loop!
```
Using synchronous `requests` in async functions blocks the event loop. Should use `httpx` with async client.

**Remediation:**
1. Replace `requests` with `httpx.AsyncClient`
2. Use connection pooling for high-throughput endpoints

### 3.3 Missing Health Checks for Downstream Services

**Severity:** MEDIUM  
**Files:** `backend/app/main.py`, `backend/app/services/`  
**Estimated Effort:** Small  
**Description:**  
Health endpoint (`/health`) returns static response without checking:
- Redis connectivity
- Supabase connectivity
- OpenRouter API availability

**Remediation:**
1. Add dependency health checks
2. Return degraded status if dependencies fail
3. Add `/health/ready` and `/health/live` endpoints (K8s compatibility)

### 3.4 Missing Structured Logging Configuration

**Severity:** MEDIUM  
**Files:** `backend/app/logging_config.py`, `backend/app/main.py`  
**Estimated Effort:** Small  
**Description:**  
`logging_config.py` exists but `main.py` uses basic `logging.basicConfig()`. JSON structured logging would help:
- Log aggregation (Datadog, ELK)
- Correlation IDs
- Searchable logs

**Remediation:**
1. Implement `structlog` for structured logging
2. Add correlation ID to trace context
3. Configure log levels per environment

### 3.5 Duplicate Supabase Clients

**Severity:** MEDIUM  
**Files:** `backend/app/services/bank_import_service.py`, `backend/app/services/recon_store.py`, `backend/app/memory_store.py`  
**Estimated Effort:** Medium  
**Description:**  
Each service creates its own Supabase client from env vars. This creates:
- Multiple connection pools
- Inconsistent client configurations
- Difficulty mocking in tests

**Remediation:**
1. Create shared `SupabaseClient` singleton
2. Use dependency injection for services
3. Add connection pooling configuration

### 3.6 Missing API Versioning Strategy

**Severity:** MEDIUM  
**Files:** `backend/app/routers/api.py`, `backend/app/routers/shopify.py`, `backend/app/routers/tiktok.py`  
**Estimated Effort:** Small  
**Description:**  
Current routes use `/api/v1/` prefix inconsistently. Some routes lack versioning, making future breaking changes difficult.

**Remediation:**
1. Standardize all routes under `/api/v1/`
2. Document breaking change policy
3. Add API version response headers

---

## 4. LOW PRIORITY — Future Improvements

### 4.1 Circuit Breaker Per-Provider, Not Global

**Severity:** LOW  
**Files:** `backend/app/ai_router.py:22-58`  
**Estimated Effort:** Small  
**Description:**  
`CircuitBreaker` is global to `AIModelRouter`. If one role's model fails, all roles are affected.

**Remediation:**
1. Implement per-role circuit breakers
2. Add circuit breaker state persistence (Redis)

### 4.2 Missing OpenAPI Documentation

**Severity:** LOW  
**Files:** All routers  
**Estimated Effort:** Medium  
**Description:**  
No endpoint-level docstrings or OpenAPI descriptions. API docs at `/docs` will be sparse.

**Remediation:**
1. Add docstrings to all endpoints
2. Document request/response schemas
3. Add examples

### 4.3 No Database Migrations System

**Severity:** LOW  
**Files:** `backend/app/services/*.py`  
**Estimated Effort:** Medium  
**Description:**  
SQLite `expense_service.py` creates tables on init. No migration system for schema changes.

**Remediation:**
1. Use Alembic for migrations
2. Version all schema changes
3. Add migration testing

### 4.4 Missing OpenTelemetry Tracing

**Severity:** LOW  
**Files:** `backend/app/trace.py`, `backend/app/ai_router.py`  
**Estimated Effort:** Medium  
**Description:**  
Custom trace context exists but no integration with OpenTelemetry for distributed tracing.

**Remediation:**
1. Add OpenTelemetry SDK
2. Instrument all HTTP calls
3. Add trace propagation

### 4.5 No Load Testing Infrastructure

**Severity:** LOW  
**Files:** `infra/`  
**Estimated Effort:** Medium  
**Description:**  
No load testing scripts or configuration. Unknown performance characteristics under load.

**Remediation:**
1. Add Locust or k6 load tests
2. Define SLOs (latency, error rate)
3. Add baseline benchmarks

---

## Sprint Recommendations

### Sprint 1 (1-2 weeks): Security Hardening
1. Rotate all secrets (Critical 1.1)
2. Fix auth bypass vulnerabilities (Critical 1.3, 1.5)
3. Add rate limiting (High 2.1)
4. Lock CORS configuration (Critical 1.4)

### Sprint 2 (1-2 weeks): Data Integrity
1. Wrap bank imports in transactions (High 2.6)
2. Fix MemoryStore error handling (High 2.3)
3. Add health checks (Medium 3.3)
4. Replace uuid.uuid4 with secure random (High 2.2)

### Sprint 3 (2-3 weeks): Technical Debt
1. Consolidate registries (High 2.4)
2. Replace requests with httpx async (Medium 3.2)
3. Add integration tests (Medium 3.1)
4. Implement structured logging (Medium 3.4)

### Sprint 4+ (Ongoing): Polish
1. API documentation
2. OpenTelemetry integration
3. Load testing
4. Frontend completeness audit

---

## Appendix: File Analysis Summary

| Category | Files | Notes |
|----------|-------|-------|
| Routers | 4 | api, shopify, tiktok, telegram (broken import) |
| Services | 30+ | Good separation of concerns |
| Agents | 2 | Ops, Finance; Supervisor orchestrator |
| Context Adapters | 9 | Claude, OpenAI, Gemini, DeepSeek, etc. |
| Bank Parsers | 3 | HSBC HK, Generic CSV, + base |
| Tests | 20+ | Good coverage of core services |

### Key Dependencies
- **FastAPI** — API framework
- **Supabase** — Database and auth
- **Redis** — State and orchestration
- **OpenRouter** — AI model routing
- **Next.js** — Frontend

### Architecture Patterns
- **Agent-based** — OpsAgent, FinanceAgent, SupervisorAgent
- **Registry pattern** — For agents, tools, and AI providers
- **Memory facade** — Supabase with in-memory fallback
- **Circuit breaker** — For AI provider resilience
