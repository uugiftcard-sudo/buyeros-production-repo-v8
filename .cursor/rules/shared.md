# Cursor Rules — Shared across all projects in this workspace
# Apply to every AI edit, review, or generation task.

---

## Universal

- **No placeholder code.** Every function, component, and module must have real, working implementations.
- **Prefer explicit over implicit.** Name things for what they are, not what they do.
- **Errors are first-class output.** Always handle errors gracefully with meaningful messages. Never swallow exceptions silently.
- **Keep changes targeted.** If you fix a bug, fix only the bug. If you refactor, refactor only what you came to refactor.

---

## TypeScript / JavaScript (CLOTH, BuyerOS, XAU)

### Imports & module resolution
- Use named imports: `import { foo } from "./bar"` — avoid `import * as bar`
- Barrel exports (index re-exports) are allowed for public package APIs
- Node.js projects use `.js` extensions in `import` statements (ESM)

### Typing
- Always annotate exported function signatures with explicit return types
- Use `type` aliases over `interface` for simple object shapes; `interface` for things that may be extended
- No `any` — use `unknown` for truly unknown values and narrow with guards
- Prefer `Record<K, V>` over `{ [key: string]: V }`

### Error handling
- Never use `console.log` for errors — use `console.error`
- Prefer `result.error` objects over throwing for expected failures in agent/tool code
- Propagate unexpected errors with context: `throw new Error(\`failed to ...: \${cause}\`, { cause })`

### Async
- Always `await` promises; never `.then()` chains for sequential async work
- Use `Promise.all()` for independent concurrent work

### React / Next.js
- Server Components by default; add `"use client"` only when browser APIs or interactivity are needed
- Use `tsx` for files with JSX; `ts` for logic-only files
- Next.js metadata via the `generateMetadata()` / `export const metadata` pattern

### Naming
- `camelCase` for variables, functions, methods
- `PascalCase` for types, interfaces, React components
- `SCREAMING_SNAKE_CASE` for module-level constants
- File names: `kebab-case.ts` for utilities, `PascalCase.tsx` for React components

---

## Python (scrapers)

### Style
- Follow **PEP 8**; line length ≤ 100
- Use `ruff` for linting — no override files needed
- 2-space indents in docstrings where needed for readability

### Type hints
- All public functions must have annotated signatures: `def foo(bar: str) -> list[ProductResult]:`
- Use `Optional[X]` from `typing`, not `X | None` (project convention)
- Use `from __future__ import annotations` at the top of every module for forward references

### Dataclasses
- Use `@dataclass` with field defaults at the bottom for optional fields
- Use `asdict()` for serialization — never manual `__dict__` copy
- Validate with Pydantic models for complex schemas; dataclasses for simple shapes

### Logging
- Module-level logger: `log = logging.getLogger(__name__)`
- Never `print()` in production code — use `log.info`, `log.warning`, `log.error`
- Log messages in English for tooling, Chinese for user-facing output in user-facing modules

### Scraping-specific
- Always respect robots.txt and rate-limit delays
- Rotate User-Agent headers per request
- Return `None` on failure rather than raising — let the caller decide how to handle

### Testing
- Use `pytest`; fixtures over manual setup in test files
- Mock external HTTP calls with `responses` or `httpx` mock

---

## Shell scripts

- Shebang: `#!/usr/bin/env bash`
- `set -euo pipefail` at the top of every script
- Double-quote all variable expansions: `"$FOO"`, not `$FOO`

---

## Git conventions

- Commit messages follow conventional format: `type(scope): description`
  - Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`
- Keep commits atomic: one logical change per commit
- Never commit secrets, `.env` files, or credentials
