# Automation Report

- Generated: 2026-05-26 02:11 UTC
- Dry run: yes

| Repo | Status | Dirty | Secret diff | Deploy gate | Blockers |
|---|---:|---:|---:|---:|---|
| BuyerOS | PASS | no | no | open | - |
| XAU | PASS | yes | no | blocked | dirty working tree blocks deploy |
| CLOTH | PASS | yes | no | blocked | dirty working tree blocks deploy |

## Notes

- BuyerOS branch: `codex/buyeros-redis-orchestration-clean`, ahead 1 / behind 0.
- XAU branch: `codex/xau-dashboard-live-ui`, ahead 0 / behind 0.
- CLOTH branch: `codex/cloth-phase2-products-filter`, ahead 0 / behind 0.
- XAU dirty evidence: `features/avatar-wardrobe/wardrobe-ui.js`, `features/avatar-wardrobe/wardrobe.html`, `features/member/member.js`.
- CLOTH dirty evidence: untracked `docs/AI_TRY_ON_CONTRACT.md`.
- No secret values are stored in this report.
- Secret-scan false-positive handling is fixed: current secret diff is `no` for all three repos.
- Full command output intentionally omitted from shared state to avoid noisy logs and accidental sensitive output.
