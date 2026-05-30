# BuyerOS Backend API

**FastAPI backend for CLOTH/BuyerOS luxury resale platform.**
Independent project under `/Documents/backend/`, integrates with BuyerOS.

## Stack

- **Framework:** FastAPI 0.115+
- **Runtime:** Python 3.11+
- **Server:** Uvicorn
- **Validation:** Pydantic 2.9+
- **HTTP Client:** httpx

## Quick Start

```bash
cd backend
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description | Default |
|---|---|---|
| `SHOPIFY_API_KEY` | Shopify API key | - |
| `SHOPIFY_STORE_URL` | Shopify store URL | `https://buyeros.myshopify.com` |
| `SHOPIFY_ACCESS_TOKEN` | Shopify access token | - |
| `TIKTOK_ACCESS_TOKEN` | TikTok API token | - |
| `TIKTOK_APP_ID` | TikTok app ID | - |
| `API_KEY` | Backend API key (Bearer auth) | `dev-key` |

**Mock mode:** All connectors run in mock mode by default when API keys are not set. No external API calls are made.

## Services

### Shopify Connector (`/shopify`)
- **Mode:** Mock (default) / Live (when `SHOPIFY_ACCESS_TOKEN` set)
- **Entities:** Products, Orders, Collections
- **Features:** CRUD operations, status management, collection summary

### TikTok Connector (`/tiktok`)
- **Mode:** Mock (default) / Live (when `TIKTOK_ACCESS_TOKEN` + `TIKTOK_APP_ID` set)
- **Features:**
  - `generate_video_pack` — structured video content for a product
  - `build_live_script` — TikTok Live streaming script
  - `build_ads_brief` — TikTok ads creative brief
- **Markets:** HK, UK

### Claim Defence (`/claim-defence`)
- Scans product copy, captions, descriptions for:
  - Forbidden words (legal/platform policy violations)
  - Misleading authenticity claims
  - Price manipulation language
  - Prohibited comparison language
- **Founder Approval Gate:** Auto-triggers when CRITICAL violation or 2+ HIGH violations found
- Sends approval request to Telegram admin bot

### Proof Score (`/proof-score`)
- Scores product authenticity based on:
  - Image count and quality signals
  - Condition and price factors
  - Brand verification
  - Market context
- Grades: A, B, C, D, F

## API Endpoints

### Shopify (`/shopify/*`)
```
GET  /shopify/status
GET  /shopify/products?collection=&market=&limit=
GET  /shopify/products/{product_id}?market=
POST /shopify/products
POST /shopify/products/{product_id}/status
GET  /shopify/orders?status=&limit=
GET  /shopify/orders/{order_id}
POST /shopify/orders
GET  /shopify/collections/summary
POST /shopify/products/{product_id}/score
POST /shopify/products/{product_id}/check
```

### Health
```
GET /health
```

## Architecture

```
backend/
├── app/
│   ├── main.py           # FastAPI app factory
│   ├── dependencies.py   # Auth dependencies (verify_api_key)
│   ├── routers/
│   │   └── shopify.py    # Shopify API routes
│   └── services/
│       ├── shopify_connector.py   # Shopify mock/live gateway
│       ├── tiktok_connector.py    # TikTok content generation
│       ├── claim_defence.py       # Fake-claim detection
│       ├── proof_score.py         # Authenticity scoring
│       └── dependencies.py
├── pyproject.toml
└── .env.example
```

## Integration with BuyerOS

This backend is designed to work alongside BuyerOS (main automation system):

- **Data flow:** BuyerOS orchestrates tasks → Shopify connector manages products/orders
- **Content generation:** TikTok connector generates content for products managed in Shopify
- **Quality control:** Claim Defence + Proof Score validate listings before publishing

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run linting
ruff check app/

# Type check
mypy app/

# Run tests
pytest
```

## Status

- [x] Shopify connector (mock mode)
- [x] TikTok connector (mock mode)
- [x] Claim Defence service
- [x] Proof Score service
- [ ] Live Shopify API integration
- [ ] Live TikTok API integration
- [ ] Telegram admin bot integration
- [ ] BuyerOS workflow integration
