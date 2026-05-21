# Agents, Providers & Context

BuyerOS is organized around shared state, not agent group chat. Agents and
external AI clients exchange context through `ContextHub`, which persists to
Supabase when configured and falls back to local memory for tests.

## Core Agents

- `Supervisor` / `BuyerOSGraphWorkflow`: routes messages to memory lookup,
  OpsAgent, FinanceAgent, or a provider.
- `OpsAgent`: handles refund, order and OCR-style tasks.
- `FinanceAgent`: handles profit, payout and settlement-style tasks.

## Provider Clients

The provider layer is intentionally thin in v1. Each provider exposes:

- `run(prompt, context)`
- `write_context(result)`

Registered providers:

- `claude`
- `cursor`
- `openai`
- `openrouter`
- `gemini`
- `deepseek`
- `minimax`
- `grok`
- `perplexity`
- `hermes`
- `openclaw`

Missing API keys must not break the system. Providers should return a clear
fallback response and still store task context when useful.

## Shared Namespaces

- `["buyeros", "refunds"]`
- `["buyeros", "finance"]`
- `["buyeros", "orders"]`
- `["buyeros", "buyers"]`
- `["buyeros", "ai_context", "<provider>"]`

## Context Endpoints

- `POST /context/write`
- `POST /context/search`
- `POST /context/summarize`
- `GET /context/session/{session_id}`
- `POST /agents/run`

When `BUYEROS_API_KEY` is configured, these endpoints require either:

- `X-Buyeros-Api-Key: <key>`
- `Authorization: Bearer <key>`

`/ping` and `/telegram/webhook` remain public.

## Audit Trail

Public context and agent API operations are written to:

- `["buyeros", "audit"]`

## Rule

Database memory is the shared brain. Agents read context, do work, and write
results back. They do not run open-ended multi-agent chat loops.
