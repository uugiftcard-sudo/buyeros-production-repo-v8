# Codex AGENTS.md — Guidelines for every Codex session in this workspace

Codex reads this file automatically at the start of every session. These guidelines
apply to all projects under `/Users/rubykan/Documents`.

---

## Who this workspace belongs to

Owner: rubykan
Projects: CLOTH (Chinese Second-Hand Luxury Marketplace), XAU (XAUUSD AI Streaming),
scrapers (Python CLI tools), BuyerOS (Next.js + Supabase buyer management system)

---

## Your personality

Be pragmatic. Get to the point. Write working code, not impressive code.
When in doubt, prefer boring technology over clever solutions.
If something is unclear, ask before guessing.

---

## Project-specific priorities

### CLOTH (npm monorepo, TypeScript)
- `agent-tasks/` contains autonomous agents (sourcing, listing, content, video, fulfillment, community, risk)
- `packages/` and `services/` follow strict module boundaries — don't cross them without good reason
- `api/` and `web/` share types via `@luxury/db`
- Always run lint + type check before finishing a task: `npm run lint && npm run check`

### scrapers (Python, pyproject.toml)
- Entry point: `scrapers` CLI — test your changes: `scrapers --help`
- Lint: `ruff check src/ tests/`
- Tests: `pytest tests/`
- No code gets committed without both passing

### BuyerOS (Next.js + Supabase)
- Edge functions live in `supabase/functions/`
- DB migrations in `supabase/migrations/` — never edit a migration after it's been applied
- Admin app uses `apps/admin/lib/supabase.ts` for the client

### XAU
- `app.js` is the main entry point — be careful with changes here

---

## Code style reminders

- TypeScript: explicit return types on all exported functions, no `any`, `camelCase` vars
- Python: type hints on all public functions, `Optional[X]` not `X | None`, `log = logging.getLogger(__name__)`
- Shell: `set -euo pipefail` at top, double-quote all `$VAR`
- Never commit `.env`, secrets, or credentials

---

## Working with this workspace

- Always confirm you're in the right project before making changes
- When fixing a bug, write a test first if a test file exists for the affected module
- If you modify shared packages (`packages/` or `services/`), run the full CI: `npm run lint && npm run check && npm run test:scenarios`
- Codex's own tools (browser, MCP servers) are available — use them when they help

---

## Automated code review on every PR

A `codex-review.yml` GitHub Actions workflow runs `codex review` on every pull request
to CLOTH and scrapers. The reviewer checks:
- Correctness: logic errors, unhandled edge cases
- Security: injection risks, exposed secrets, unsafe patterns
- Style: compliance with these guidelines
- Tests: coverage of new behavior

When reviewing, comment directly on the relevant lines in the PR with specific,
actionable feedback. Use the `<!-- comment -->` format so the author can reply in-thread.

---

## Communication

- Language: respond in the same language the user used
- Explain *why* a change is needed, not just *what* changed
- If you don't know something, say so — don't fabricate
