# Face Swap Benchmark — Team Handoff

## Current status
- Project folder: `/Users/rubykan/Documents/Codex/2026-05-22/new-chat-2`
- Core report folder: `/Users/rubykan/Documents/Codex/2026-05-22/new-chat-2/reports/face_swap_benchmark`
- Main collaboration plan: `/Users/rubykan/Documents/Codex/2026-05-22/new-chat-2/reports/face_swap_benchmark/AGENT_COLLABORATION_PLAN.md`
- Untested provider manual methods: `/Users/rubykan/Documents/Codex/2026-05-22/new-chat-2/reports/face_swap_benchmark/untested_manual_methods.md`
- RunPod GPU rerun guide: `/Users/rubykan/Documents/Codex/2026-05-22/new-chat-2/reports/face_swap_benchmark/rerun_first_gpu_facefusion_guide.md`

## Objective
Finish an evidence-backed benchmark report comparing authorized video face-swap methods by identity similarity, realism, edge blend, motion stability, ease, cost, and productization.

## Current evidence
- Tested rows exist in `reports/face_swap_benchmark/results.csv`.
- Akool Face Swap Plus V4 is currently best: identity=3.4, realism=3.8, weighted=3.64, verdict=reject_or_retry (watermark visible, identity still <4 gate).
- DeepLiveCam / FaceFusion local baselines are stable but not similar enough (weighted ~2.6-2.85).
- No current 15s upgrade candidate.
- Source face count remains insufficient for serious DeepFaceLab/faceswap training.

## Active blockers
- Need more provider outputs before final ranking.
- Need 15-30 source faces minimum for training route; 30-100 preferred.
- API keys/payment/invite-code steps are human-only; agents must not store secrets.
- SaaS browser tests blocked: Magic Hour (0 credits), GoEnhance AI (not logged in + no tokens), DeepSwap (requires login/signup).

## Browser test results (2026-05-27)
- Magic Hour: BLOCKED — account has 0 credits; human needs to claim daily 100 free credits or buy credit pack ($10 Starter/4000 credits).
- GoEnhance AI: BLOCKED — account not logged in; human needs login + 30 free tokens; API requires key+token purchase.
- DeepSwap: BLOCKED — app page requires login/signup before upload; no output.
- Akool: TESTED (manual) — weighted=3.64, best so far but watermark + identity<4.
- RunPod FaceFusion CUDA: GUIDE READY — human needs to execute steps in `rerun_first_gpu_facefusion_guide.md`.

## Next actions
1. Run manual SaaS tests from `untested_manual_methods.md`, starting with Magic Hour / GoEnhance / ModelsLab / DeepSwap / Remaker.
2. Re-run RunPod FaceFusion CUDA direct using `rerun_first_gpu_facefusion_guide.md`.
3. Put downloaded mp4 files into `reports/face_swap_benchmark/result_inbox/`.
4. Import and rebuild reports:

```bash
cd /Users/rubykan/Documents/Codex/2026-05-22/new-chat-2
python3 scripts/common/import_result_inbox.py
bash scripts/common/rebuild_all_reports.sh
```

## Verification commands
```bash
cd /Users/rubykan/Documents/Codex/2026-05-22/new-chat-2
bash scripts/common/rebuild_all_reports.sh
open reports/face_swap_benchmark/index.html
open reports/face_swap_benchmark/tested_outputs.html
open reports/face_swap_benchmark/untested_manual_methods.html
```

## Handoff rule
Every agent must report provider, status, output path, watermark, audio, cost/credits, main issue, and next action.
