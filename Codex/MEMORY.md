# Codex Shared Memory — workspace knowledge base
# Codex automatically loads this at the start of every session.
# Add notes here when you learn something worth remembering across sessions.

---

## Workspace Owner
rubykan

## Projects

### CLOTH — Chinese Second-Hand Luxury Fashion Marketplace
- **Path**: `/Users/rubykan/Documents/CLOTH`
- **Stack**: TypeScript monorepo (npm workspaces), Next.js, Node.js agents
- **Markets**: UK, HK (and more — filter by `market` field)
- **Agent tasks**: sourcing, listing, content, video, fulfillment, community, risk — orchestrated by `agent-tasks/dispatcher.ts`
- **CI**: GitHub Actions with `npm run lint && npm run check && npm run test:scenarios`
- **Shared types**: `@luxury/db` package
- **Rules**: `.cursor/rules/project.md`

### scrapers — Python CLI for web scraping
- **Path**: `/Users/rubykan/Documents/scrapers`
- **Stack**: Python 3.11+, `requests`, `BeautifulSoup`, `click`, `pydantic`
- **Entry point**: `scrapers` CLI (defined in pyproject.toml)
- **Linting**: `ruff check src/ tests/` (line-length: 100)
- **Tests**: `pytest tests/`
- **CI**: runs on Python 3.11, 3.12, 3.13
- **Rules**: `.cursor/rules/project.md`

### BuyerOS — Buyer Management System
- **Path**: `/Users/rubykan/Documents/_Organized/Claude/Claude/Projects/買手對象系統`
- **Stack**: Next.js + Supabase (Edge functions + migrations)
- **Admin UI**: `apps/admin/`
- **Backend**: `supabase/functions/` (customers, orders, transactions, refunds, dashboard, telegram-webhook)
- **DB migrations**: `supabase/migrations/` — do not edit after applying

### XAU — XAUUSD AI Strategy Streaming Platform
- **Path**: `/Users/rubykan/Documents/XAU`
- **Stack**: Node.js + TypeScript, Docker
- **Entry point**: `app.js`
- **No CI workflows yet**

---

## Codex Configuration

- Global config: `~/.codex/config.toml`
- Model: `gpt-5.5` with `pragmatic` personality
- Session history: `~/Documents/Codex/` (organized by date)
- Workspace Codex config: `~/Documents/Codex/.codex/environments/environment.toml`
- Auto-reviewer: `guardian_subagent` approval mode enabled
- Theme: `inspired-github`

---

## Shared Patterns

### TypeScript error shape (CLOTH agents)
```typescript
type AgentResult = {
  agentId: string;
  status: "ok" | "error";
  startedAt: string;    // ISO 8601
  completedAt: string;   // ISO 8601
  durationMs: number;
  market: string;
  itemsProcessed?: number;
  tasksGenerated?: number;
  escalations?: string[];
  errors?: string[];
};
```

### Python scraping result shape (scrapers)
```python
@dataclass
class ProductResult:
    asin: str = ""
    title: str = ""
    price: str = ""
    # ... full fields in amazon_monitor.py
    scraped_at: str = ""  # datetime.now().isoformat(timespec="seconds")
```

### Git commit convention
```
<type>(<scope>): <description>
types: feat | fix | chore | docs | refactor | test | ci
```

---

## Reminders

- Never commit `.env`, `node_modules`, or any file with credentials
- All TypeScript exports need explicit return types
- All Python public functions need type annotations
- Codex review runs on every PR to `main` via `codex-review.yml`
- Codex loads `.cursor/rules/shared.md` and `.cursor/rules/project.md` for style guidance
