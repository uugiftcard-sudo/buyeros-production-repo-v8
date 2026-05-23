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
│   ├── cli.py              # Click CLI entry point
│   ├── config.py           # Config loader (yaml + env)
│   ├── logging_config.py   # Structured logging setup
│   ├── models/             # Pydantic data models
│   ├── scrapers/           # Platform scraper implementations
│   ├── storage/            # CSV + JSON output writers
│   └── utils/              # HTTP client + HTML helpers
├── tests/                  # Unit tests
├── config.yaml             # All configuration
├── .env.example            # API keys template
├── Dockerfile              # Multi-stage Docker image
├── docker-compose.yml      # Docker Compose setup
├── .dockerignore           # Docker build exclusions
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

## Development

```bash
make install   # Install + dev dependencies
make test      # Run pytest
make lint      # Run ruff linter
make lint-fix  # Auto-fix lint issues
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
