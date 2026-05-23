# scrapers — Professional Multi-Platform Scraping CLI

> Structured, rate-limited, retry-aware web scraping toolkit for multiple platforms.
> Built with Python 3.11+, Click, Pydantic, and Rich.

---

## Features

| Scraper | Description |
|---------|-------------|
| **LinkedIn** | Public profile scraper — name, headline, company, industry, location. Keyword search via Google. |
| **B2B Contact** | Apollo.io + Hunter.io + Companies House UK — find professional contacts by domain or keyword. |
| **Trip.com** | Flights, hotels, and attractions — price, schedule, ratings. |
| **Amazon** | Product search and ASIN detail — price, rating, rank, badges. Multi-domain (.com / .co.uk). |
| **eBay** | Product search and seller profiles — price, condition, seller ratings. |
| **Loyalty** | Nectar & Tesco Clubcard balance checker + Amazon gift card balance. |
| **Supermarket** | UK supermarket price comparison — John Lewis, Tesco, M&S. |
| **Playwright** | Headless browser scraper for JS-heavy pages (Amazon, Tesco). |

### Architecture Highlights

- **Unified CLI** — single `scrapers` entry point with rich colored output
- **BaseScraper** — shared retry logic, rate limiting, User-Agent rotation, error handling
- **Pydantic models** — all scraped data is typed and validated
- **Configurable** — all settings via `config.yaml` and environment variables
- **Multiple output formats** — CSV and JSON with automatic directory creation
- **Dry-run mode** — validate inputs without making network requests
- **Docker-ready** — multi-stage Dockerfile + docker-compose with named volume

---

## Installation

```bash
# Clone / navigate to project
cd scrapers

# Install in editable mode (recommended)
pip install -e ".[dev]"

# Or via requirements
pip install -r requirements.txt
```

### Prerequisites

- Python 3.11 or higher
- API keys (optional, for B2B scraper):
  ```bash
  cp .env.example .env
  # edit .env and add your APOLLO_API_KEY / HUNTER_API_KEY
  ```

---

## Usage

### Global Options

| Option | Description |
|--------|-------------|
| `--output, -o` | Output file path (default: auto-generated per scraper) |
| `--format, -f` | Output format: `csv` or `json` (default: `csv`) |
| `--verbose, -v` | Enable verbose (DEBUG) logging |
| `--dry-run` | Validate inputs without making network requests |

### Scraper Commands

#### LinkedIn
```bash
# Single profile
scrapers linkedin https://uk.linkedin.com/in/johndoe

# Batch from file (one URL per line)
scrapers linkedin -f urls.txt

# Keyword search via Google
scrapers linkedin -k "software engineer London UK" --search-limit 20

# Output JSON
scrapers linkedin https://uk.linkedin.com/in/johndoe -f json
```

#### B2B Contact Finder
```bash
# Find contacts by company domain (Apollo + Hunter)
scrapers b2b --domain acme.com

# Apollo keyword search
scrapers b2b --apollo-keyword "sales manager" --country GB

# UK company search (no API key needed)
scrapers b2b --company "Acme Ltd"

# Specific platform only
scrapers b2b --domain acme.com --platform apollo
```

#### Trip.com
```bash
# Search flights
scrapers trip --type flight --from LHR --to NRT --date 2025-06-15

# Search hotels
scrapers trip --type hotel --city london --checkin 2025-06-15 --checkout 2025-06-18

# Search attractions
scrapers trip --type attraction --city paris --keyword "Eiffel Tower"

# Output JSON
scrapers trip --type flight --from SYD --to SIN --date 2025-07-01 -f json
```

#### Amazon
```bash
# Search by keyword (default: amazon.com)
scrapers amazon --keyword "wireless headphones"

# UK domain, multiple pages
scrapers amazon --keyword "laptop" --domain co.uk --pages 3

# Get specific ASINs
scrapers amazon --asin B09V3KXJPB,B07XGY4Y1G
```

#### eBay
```bash
# Search products
scrapers ebay --search "iphone 15 pro"

# Filter by price range and condition
scrapers ebay --search "macbook" --max-price 1500 --condition used

# Get seller profiles
scrapers ebay --seller johndoe_uk,janeshop123
```

#### Loyalty Checker
```bash
# Nectar points (interactive — will prompt for credentials)
scrapers loyalty --nectar

# Tesco Clubcard
scrapers loyalty --tesco

# Amazon gift card balance
scrapers loyalty --amazon-gc
```

#### UK Supermarket
```bash
# Price comparison across all supermarkets
scrapers supermarket -c -k "whole milk"

# Specific retailer
scrapers supermarket -r john-lewis -k "dyson vacuum"
scrapers supermarket -r tesco -k "chicken breast"
scrapers supermarket -r ms -k "sandwich"
```

---

## Configuration

All settings live in `config.yaml`. Environment variables override file values.

```bash
# .env
APOLLO_API_KEY=your_key
HUNTER_API_KEY=your_key
OUTPUT_DIR=./output
DEFAULT_DELAY=2.0
MAX_RETRIES=3
LOG_LEVEL=INFO
```

Key settings you can override:

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `./output` | Output directory for results |
| `DEFAULT_DELAY` | `2.0` | Default delay between requests (seconds) |
| `MAX_RETRIES` | `3` | Maximum retry attempts |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Project Structure

```
scrapers/
├── src/
│   ├── __init__.py
│   ├── cli.py              # Click CLI entry point
│   ├── config.py           # Config loader (yaml + env)
│   ├── logging_config.py   # Structured logging setup
│   ├── types.py            # Shared TypedDict types
│   ├── metrics.py          # Prometheus metrics
│   ├── cache.py            # Redis cache layer
│   ├── observability.py    # structlog + Sentry setup
│   ├── jobs.py             # Background job queue
│   ├── dashboard.py        # Live terminal dashboard
│   ├── api/
│   │   └── server.py      # FastAPI REST API
│   ├── models/             # Pydantic data models
│   ├── scrapers/           # Platform scraper implementations
│   │   ├── base.py         # BaseScraper (sync, retries)
│   │   ├── async_base.py   # AsyncBaseScraper (concurrent)
│   │   ├── browser_scraper.py
│   │   ├── amazon.py
│   │   ├── amazon_browser.py
│   │   └── ...
│   ├── storage/            # CSV + JSON output writers
│   └── utils/              # HTTP client + HTML helpers
├── tests/                  # Unit tests
├── config.yaml             # All configuration
├── .env.example            # API keys template
├── .pre-commit-config.yaml # Pre-commit hooks
├── Dockerfile              # Multi-stage Docker image
├── docker-compose.yml      # Docker Compose setup
├── Makefile                # Development commands
└── pyproject.toml          # Package definition
```

---

## Docker

Run the scrapers inside a container — no Python installation needed on your host.

```bash
# 1. Build the image
make docker-build

# 2. Set up your API keys
cp .env.example .env
# edit .env and add your APOLLO_API_KEY / HUNTER_API_KEY

# 3. Run any scraper
make docker-run SCRAPER_ARGS='amazon --keyword laptop --pages 2'
make docker-run SCRAPER_ARGS='supermarket -c -k "whole milk"'
make docker-run SCRAPER_ARGS='ebay --search iphone'
make docker-run SCRAPER_ARGS='b2b --domain acme.com'
make docker-run SCRAPER_ARGS='trip --type flight --from LHR --to NRT --date 2026-06-15'

# 4. Results appear in ./output/ on your host
ls output/
```

### Docker Compose quick examples

```bash
# Quick run with pre-configured examples
docker compose up --rm amazon-keyword
docker compose up --rm supermarket-compare
docker compose up --rm ebay-search

# Interactive loyalty checker
docker compose run --rm scrapers
```

### Manual Docker run

```bash
docker run --rm -it \
  -v $(pwd)/output:/app/output \
  -e APOLLO_API_KEY=xxx \
  -e HUNTER_API_KEY=yyy \
  scrapers amazon --keyword laptop
```

---

## Pro Features

### FastAPI Server

Run the REST API to enqueue scrape jobs asynchronously and poll for results.

```bash
pip install -e ".[pro]"
make api
# → http://localhost:8000/docs  (Swagger UI)
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/scrape` | Enqueue a scrape job |
| `GET` | `/scrape/{job_id}` | Get job status + results |
| `GET` | `/jobs` | List recent jobs |
| `DELETE` | `/scrape/{job_id}` | Delete a job |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

**Example:**

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"scraper": "amazon", "params": {"keyword": "laptop", "pages": 2}}'
```

### Dashboard

Live terminal dashboard showing job queue status and metrics.

```bash
make dashboard
```

Starts the API + renders a Rich Live view of all jobs. Press Ctrl+C to exit.

### Async Scraper

For high-throughput batch scraping, use the async base class:

```python
from src.scrapers.async_base import AsyncBaseScraper

class MyAsyncScraper(AsyncBaseScraper[MyItem]):
    name = "my_scraper"

    async def scrape_item(self, url: str, client: httpx.AsyncClient) -> MyItem | None:
        resp = await client.get(url)
        return MyItem.model_validate_json(resp.text)

result = await scraper.scrape_batch(urls)
```

### Redis Cache

Enable response caching to avoid re-scraping the same URLs:

```bash
redis-server &
# Set REDIS_URL=redis://localhost:6379/0 in .env
```

```python
from src.cache import Cache

cache = Cache(ttl=1800)  # 30-minute TTL
cached = cache.get("amazon", "laptop")
if cached is None:
    results = scraper.search("laptop")
    cache.set("amazon", "laptop", results)
```

### Prometheus Metrics

Metrics are exposed at `/metrics` on the API server:

```bash
curl http://localhost:8000/metrics | grep scraper_requests
curl http://localhost:8000/metrics | grep scraper_active
curl http://localhost:8000/metrics | grep scraper_cache
```

Metrics available:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `scraper_requests_total` | Counter | scraper, status | Total requests |
| `scraper_duration_seconds` | Histogram | scraper | Scrape duration |
| `scraper_active_scrapes` | Gauge | scraper | Currently running |
| `scraper_cache_hits_total` | Counter | scraper | Cache hits |
| `scraper_cache_misses_total` | Counter | scraper | Cache misses |
| `scraper_queued_jobs` | Gauge | — | Pending queue depth |
| `scraper_completed_jobs_total` | Counter | scraper, outcome | Completed jobs |

### Sentry Error Tracking

```bash
SENTRY_DSN=https://xxxxx@o123.ingest.sentry.io/456 scrapers amazon ...
```

Errors are automatically captured with full stack traces and request context.

### Pre-commit Hooks

```bash
make setup-hooks
```

Runs `ruff format` + `ruff check` on staged files before every commit.

### Full Installation

```bash
pip install -e ".[full]"
# or
make install-full
```

---

## Development

```bash
make install        # Install base + dev dependencies
make install-pro   # Install base + pro (FastAPI, Redis, Prometheus)
make install-full  # Install everything
make test          # Run pytest
make lint          # Run ruff linter
make lint-fix      # Auto-fix lint issues
make api           # Start FastAPI REST API
make dashboard     # Start API + live terminal dashboard
make scrape ARGS='...'  # Run scraper locally
```

### Running tests

```bash
make test
# or directly:
pytest tests/ -v
```

### Docker development

```bash
make docker-build      # Build image
make docker-run SCRAPER_ARGS='...'  # Run in container
make docker-clean      # Remove containers + images
```

---

## ⚠️ Legal Disclaimer

**This tool is for educational and personal use only.**

- Respect robots.txt and platform Terms of Service
- Do not use for unauthorized data collection, harassment, or unsolicited marketing
- Some platforms may require authentication or paid API access — use official APIs where available
- The authors accept no liability for misuse of this software
- **LinkedIn**: Only scrape publicly visible information; avoid automated mass collection
- **Amazon/eBay**: Use for personal price monitoring only
- **Loyalty**: Only query your own accounts; never store passwords in plain text
