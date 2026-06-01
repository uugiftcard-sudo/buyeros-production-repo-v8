# BuyerOS Backend — Project Scope

## Overview

BuyerOS Backend is a FastAPI microservice platform powering the CLOTH luxury resale platform. It provides external API integrations (Shopify, TikTok), AI-powered routing and orchestration, financial reconciliation, OCR/vision services, and an admin Telegram bot.

## Tech Stack

- **Framework:** FastAPI 0.115+
- **Runtime:** Python 3.11+
- **Server:** Uvicorn
- **Validation:** Pydantic 2.9+
- **HTTP Client:** httpx
- **AI Context:** Claude, OpenAI, DeepSeek, Gemini, Grok, MiniMax, Perplexity, OpenRouter, OpenClaw, Cursor

## Service Map

### Connectors
| Service | File | Purpose | Status |
|---|---|---|---|
| Shopify | `services/shopify_connector.py` | Shopify API gateway | DONE (mock) |
| TikTok | `services/tiktok_connector.py` | TikTok content generation | DONE (mock) |
| XAU | `services/xau_integration.py` | XAU platform sync | DONE (mock) |
| CLOTH | `services/cloth_integration.py` | CLOTH platform sync | DONE (mock) |

### Finance
| Service | File | Purpose | Status |
|---|---|---|---|
| Expense | `services/expense_service.py` | Expense tracking | DONE |
| Bank Import | `services/bank_import_service.py` | Bank statement import | DONE |
| Bank Manual | `services/bank_manual_import.py` | Manual bank import | DONE |
| Bank Parsers | `services/bank_parsers/` | HSBC HK, Generic parsers | DONE |
| Recon Store | `services/recon_store.py` | Reconciliation storage | DONE |
| Recon Matching | `services/recon_matching.py` | Auto-reconciliation | DONE |
| Finance Service | `services/finance_service.py` | Finance operations | DONE |
| Finance Sheets | `services/finance_sheets.py` | Google Sheets sync | TODO |
| Reporting | `services/reporting_service.py` | Report generation | DONE |

### Vision/OCR
| Service | File | Purpose | Status |
|---|---|---|---|
| Receipt Vision | `services/receipt_vision_service.py` | Receipt OCR | DONE |
| OCR Tools | `tools/ocr.py` | OCR utilities | DONE |
| Refund Tools | `tools/refund.py` | Refund processing | DONE |

### AI/Agents
| Service | File | Purpose | Status |
|---|---|---|---|
| AI Router | `ai_router.py` | Model routing | DONE |
| Orchestration | `orchestration.py` | Task orchestration | DONE |
| Supervisor | `supervisor.py` | Agent supervision | DONE |
| Registry | `registry.py` | Service registry | DONE |
| Finance Agent | `agents/finance_agent.py` | Finance AI agent | DONE |
| Ops Agent | `agents/ops_agent.py` | Operations AI agent | DONE |
| Context Hub | `context/context_hub.py` | Context management | DONE |
| Provider Registry | `context/provider_registry.py` | AI provider registry | DONE |

### Context Adapters
| Adapter | File | Provider |
|---|---|---|
| Claude | `context/adapters/claude.py` | Anthropic |
| OpenAI | `context/adapters/openai.py` | OpenAI |
| DeepSeek | `context/adapters/deepseek.py` | DeepSeek |
| Gemini | `context/adapters/gemini.py` | Google |
| Grok | `context/adapters/grok.py` | xAI |
| MiniMax | `context/adapters/minimax.py` | MiniMax |
| Perplexity | `context/adapters/perplexity.py` | Perplexity |
| OpenRouter | `context/adapters/openrouter.py` | OpenRouter |
| OpenClaw | `context/adapters/openclaw.py` | OpenClaw |
| Cursor | `context/adapters/cursor.py` | Cursor |

### Core
| Service | File | Purpose | Status |
|---|---|---|---|
| Session Store | `services/session_store.py` | Session persistence | DONE |
| Memory Store | `services/memory_store.py` | Memory persistence | DONE |
| Memory Timeline | `services/memory_timeline_service.py` | Timeline events | DONE |
| Audit | `audit.py` | Audit logging | DONE |

### Ops
| Service | File | Purpose | Status |
|---|---|---|---|
| Telegram | `services/telegram.py` | Admin bot | TODO |
| Telegram Commands | `services/telegram_commands.py` | Bot commands | DONE |
| Task Dispatcher | `services/task_dispatcher_service.py` | Task routing | DONE |
| Ops Status | `services/ops_status_service.py` | Ops status tracking | DONE |

### Adapters (Payment/Platform)
| Adapter | File | Purpose |
|---|---|---|
| Base | `services/adapters/base_adapter.py` | Adapter interface |
| Shopify | `services/adapters/shopify_adapter.py` | Shopify adapter |
| Stripe | `services/adapters/stripe_adapter.py` | Stripe adapter |
| PayPal | `services/adapters/paypal_adapter.py` | PayPal adapter |
| Custom | `services/adapters/custom_adapter.py` | Custom adapter |
| Custom Ecom | `services/adapters/custom_ecom_adapter.py` | Custom ecom adapter |

### Admin
| Service | File | Purpose | Status |
|---|---|---|---|
| Admin Dashboard | `services/admin_dashboard.py` | Admin HTML renderer | DONE |
| Claim Defence | `services/claim_defence.py` | Fake claim detection | DONE |
| Proof Score | `services/proof_score.py` | Authenticity scoring | DONE |

### Workflows
| Service | File | Purpose | Status |
|---|---|---|---|
| BuyerOS Graph | `workflows/buyeros_graph.py` | Workflow graph | DONE |
| Workflow Main | `workflows/main.py` | Workflow entry | DONE |

### Automation
| Service | File | Purpose | Status |
|---|---|---|---|
| Business Automation | `services/business_automation.py` | Business logic | DONE |
| Canonical Workspace | `services/canonical_workspace.py` | Workspace management | DONE |

## Integration Architecture

```
BuyerOS (orchestrator)
    ↓
Backend API (FastAPI)
    ├── Shopify Connector → CLOTH Shopify store
    ├── TikTok Connector → TikTok content
    ├── Finance Services → Bank + Sheets
    │   ├── Expense Service
    │   ├── Bank Import (HSBC HK, Generic)
    │   ├── Recon Matching
    │   └── Recon Store
    ├── Vision Services → Receipt OCR
    ├── AI Agents → Finance + Ops agents
    │   ├── AI Router → Multi-provider routing
    │   ├── Orchestration → Task orchestration
    │   └── Context Hub → Multi-adapter context
    └── Telegram Bot → Admin notifications
```

## Router Endpoints

### Shopify Router (`app/routers/shopify.py`)
- Product CRUD, status management, collections
- Order management
- Score and check endpoints

### TikTok Router (`app/routers/tiktok.py`)
- Video pack generation
- Live script builder
- Ads brief creator

## TODO Priority

1. **P0 — Core**: AI Router, Orchestration, Supervisor (foundation)
2. **P1 — Finance**: Expense service, Bank import, Recon matching (business critical)
3. **P2 — Connectors**: Shopify live, TikTok live (revenue)
4. **P3 — Vision**: Receipt OCR (efficiency)
5. **P4 — Ops**: Telegram bot (UX)

## Current Status

- ✅ Mock connectors working (Shopify, TikTok, XAU, CLOTH)
- ✅ 10 AI context adapters (Claude, OpenAI, DeepSeek, Gemini, Grok, etc.)
- ✅ Finance pipeline (expense, bank import, reconciliation)
- ✅ Payment adapters (Shopify, Stripe, PayPal)
- ✅ Admin services (dashboard, claim defence, proof score)
- ✅ Workflow automation
- ⏳ Finance Sheets sync (Google Sheets integration)
- ⏳ Telegram bot live integration
- ⏳ Need: API keys, integration testing, live connectors

## Service Count

- **Connectors:** 4
- **Finance:** 9
- **Vision/OCR:** 3
- **AI/Agents:** 8
- **Context Adapters:** 10
- **Core:** 4
- **Ops:** 4
- **Adapters:** 6
- **Admin:** 3
- **Workflows:** 2
- **Automation:** 2

**Total: 55+ services and modules**
