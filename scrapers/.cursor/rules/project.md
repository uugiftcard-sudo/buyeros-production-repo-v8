# Cursor Rules — scrapers project
# Extends: .cursor/rules/shared.md

# Additional rules specific to the Python scraping CLI

---

## scrapers Project Conventions

### CLI entry point
- The `scrapers` CLI is defined in `src/cli.py` or a `pyproject.toml` script entry
- All CLI arguments must have `--help` descriptions in Chinese when user-facing, English otherwise
- Use `argparse.RawDescriptionHelpFormatter` for multi-line examples

### HTTP layer
- All external HTTP calls go through a thin wrapper that handles:
  - User-Agent rotation
  - Retry with exponential backoff (3 attempts)
  - Status code checks (503 / 429 → backoff + retry; 4xx → fail fast)
  - Timeout (default 20s)
- Never make raw `requests.get()` calls in business logic

### Data models
- All scraped entities are `@dataclass` with field defaults at the bottom
- `ProductResult`, `PriceHistoryEntry`, and similar data classes are defined once, near the function that first uses them
- Serialize with `asdict()` — do not manually copy `__dict__`

### File output
- CSV columns are defined once as a list of strings at the top of the `save_csv` function
- Use `newline=""` when opening CSV files
- Always use `encoding="utf-8-sig"` for CSV (Excel compatibility)
- JSON uses `ensure_ascii=False, indent=2`

### Testing
- Unit tests live in `tests/`, mirror the `src/` structure
- Mock HTTP responses with `responses.RequestMock` or `httpx.Response`
- Use `pytest` fixtures for shared setup (tmp dirs, mock config)

### Linting & type checking
- `ruff check src/ tests/` must pass with zero errors before commit
- `mypy src/ --ignore-missing-imports` must pass with zero errors before commit
- CI runs on Python 3.11, 3.12, 3.13 — test your code on all three if possible

### Ethical scraping
- Always respect `robots.txt`
- Add configurable per-domain delays (default ≥ 2s)
- Log a compliance reminder docstring at the top of each scraper module
- Do not scrape behind authentication without explicit permission
