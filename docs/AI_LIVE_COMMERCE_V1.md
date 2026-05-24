# AI Live Commerce v1

## Goal

Deliver a safe, demo-ready AI virtual host workflow for XAU live rooms and CLOTH commerce selling flows.

## What v1 supports

- XAU live script API returns:
  - hook
  - story beat
  - interaction prompt
  - CTA
  - risk reminder
- XAU live state supports:
  - topic
  - CTA
  - presenter
  - account style
  - live mode
  - news alerts for live room and app display
- CLOTH live-selling API returns:
  - product-based script
  - interaction prompts
  - inventory guardrail
  - finance estimate
  - support notes
- BuyerOS dispatcher supports:
  - `commerce` + `live_selling`
  - `xau` + `live_stream`
  - timeline records for routing and run-all execution

## Compliance boundary

Allowed:

- Real audience growth playbooks.
- Multi-account content strategy when accounts are genuine brand/content channels.
- Demo-only simulated audience prompts clearly labelled for internal rehearsal.
- AI virtual host disclosed as AI presenter.

Not allowed:

- Fake followers.
- Fake comments.
- Fake viewers.
- Undisclosed human impersonation.
- Buying or coordinating "水軍" engagement.

## Smoke commands

```bash
cd /Users/rubykan/Documents/XAU
npm run test:server
curl -sS http://127.0.0.1:3099/api/news/latest
curl -sS -X POST http://127.0.0.1:3099/api/ai/script \
  -H "Content-Type: application/json" \
  -d '{"biasType":"wait","topic":"XAU AI live stream","cta":"留言黃金","accountStyle":"educational"}'
```

```bash
cd /Users/rubykan/Documents/CLOTH
PORT=3002 npm run dev --workspace=api
curl -sS http://127.0.0.1:3002/api/live/readiness
curl -sS -X POST http://127.0.0.1:3002/api/live/selling-plan \
  -H "Content-Type: application/json" \
  -d '{"productId":"p001","accountStyle":"luxury_editor","cta":"留言想看細節圖"}'
```

```bash
cd /Users/rubykan/Downloads/buyeros-production-repo-v8
curl -sS -X POST "$PUBLIC_BASE_URL/tasks/dispatch_plan" \
  -H "Authorization: Bearer $BUYEROS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project":"commerce","task_type":"live_selling","title":"AI live selling smoke","prompt":"Plan one AI virtual host livestream selling flow with inventory and finance checks."}'
```
