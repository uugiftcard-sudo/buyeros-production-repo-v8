# Three Repo Automation Controller

This folder contains the shared controller for BuyerOS, XAU, and CLOTH.

It is intentionally outside the product repos. It stores no secrets and does not
read or print `.env` values.

## Modes

```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all
python3 /Users/rubykan/Documents/team/automation/run.py deploy --repo buyeros
python3 /Users/rubykan/Documents/team/automation/run.py report --repo all --write-state
```

Use `--dry-run` to list the commands without executing checks or deploy steps:

```bash
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run
```

Dry runs still show blockers, but exit `0` by default. Add `--strict-exit` if
you want dry-run blockers to fail a CI job.

## Safety gates

- Dirty working tree blocks deploy.
- Secret-like patterns in git diff block deploy.
- Failed check commands block deploy.
- PR hygiene is reported for each repo: branch, upstream, ahead/behind, and `gh pr status` when available.
- BuyerOS deploy uses existing `infra/deploy_and_smoke.sh`.
- XAU deploy is local Docker only.
- CLOTH has no deploy target in v1, so deploy reports a blocker.

## UI/runtime smoke

`check` includes lightweight HTTP smoke checks through `smoke_http.py`.
When needed, `with_server.py` starts a temporary local dev server, waits for a
ready URL, runs the smoke, then terminates that server.

Default URLs:

- BuyerOS: `http://127.0.0.1:3000`
- XAU: `http://127.0.0.1:3002`
- CLOTH API: `http://127.0.0.1:3001`

To run a smoke directly against an already-running server, override with:

```bash
TEAM_AUTOMATION_BUYEROS_URL=http://127.0.0.1:3000 \
TEAM_AUTOMATION_XAU_URL=http://127.0.0.1:3112 \
TEAM_AUTOMATION_CLOTH_URL=http://127.0.0.1:3001 \
python3 /Users/rubykan/Documents/team/automation/run.py check --repo all
```

The smoke script does not print secrets and only checks page/API availability,
basic JSON shape, and expected route availability.

## Reports

Successful non-dry runs write:

- `/Users/rubykan/Documents/team/automation/latest-report.md`

Pass `--write-state` to also update:

- `/Users/rubykan/Documents/team/state.md`

Only the summary table is written to `state.md`; detailed command output stays
in `latest-report.md`.

## Scheduling

- GitHub PR checks should stay in each product repo's GitHub Actions workflows.
- Local scheduled status checks can be created in the Codex app as a heartbeat
  that runs `python3 /Users/rubykan/Documents/team/automation/run.py check --repo all --dry-run`.
- Active Codex heartbeat: `three-repo-automation-monitor`, every 30 minutes.
- Codex app heartbeats depend on the app/session being available; they are not a
  replacement for GitHub Actions or production monitoring.
- Production deploy is intentionally not scheduled. Use manual `deploy` mode.
