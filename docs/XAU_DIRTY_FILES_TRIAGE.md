# XAU Dirty Files Triage

Last verified: 2026-05-24

Source repo: `/Users/rubykan/Documents/XAU`

This file records the local XAU dirty tree so another AI can keep writing features without accidentally mixing unrelated work into one large PR.

## Current Dirty List

```text
M  stream/live-24h-engine.js
M  stream/obs-control-panel.html
?? analytics/
?? features/avatar-integration/
?? landing/
?? promo/README.md
?? promo/xau-poster-v1.html
?? promo/xau-reel-story-v1.html
?? server/routes/tts.js
?? server/services/ttsService.js
?? stream/live-automation-scheduler.js
?? stream/live-engine-v2.html
?? stream/obs-control-panel.js
?? stream/obs-overlay-v2.html
?? stream/obs-scene-controller.js
?? stream/script-rotator-v2.js
?? stream/stream-analytics.html
?? stream/stream-analytics.js
?? stream/stream-engagement-v2.js
```

## Important Context

`server/routes/tts.js` and `server/services/ttsService.js` were already added to merged XAU PR #3 through a clean temporary worktree. The local copies may now be stale duplicates or separate variants. Do not blindly commit them from the dirty working tree.

## Recommended PR Split

### PR A: OBS Control And Overlay Stability

Scope:

```text
stream/obs-control-panel.html
stream/obs-control-panel.js
stream/obs-overlay-v2.html
stream/obs-scene-controller.js
```

Goal:

- OBS panel loads without console errors.
- Missing API data shows fallback state.
- Buttons call existing XAU API routes only.

Verification:

```bash
cd /Users/rubykan/Documents/XAU
npm test --prefix server
```

Manual/browser:

```text
Open stream/obs-control-panel.html
Open stream/obs-overlay-v2.html
Check browser console for errors
```

### PR B: Live Scheduler And Script Rotator

Scope:

```text
stream/live-24h-engine.js
stream/live-automation-scheduler.js
stream/live-engine-v2.html
stream/script-rotator-v2.js
```

Goal:

- Scheduler can choose session/language/time block.
- Script rotator can call `/api/ai/script`.
- No infinite loops or timer leaks.

Verification:

```bash
cd /Users/rubykan/Documents/XAU/server
npm test
```

Additional checks to add if missing:

```bash
node --check ../stream/live-automation-scheduler.js
node --check ../stream/script-rotator-v2.js
node --check ../stream/live-24h-engine.js
```

### PR C: Stream Analytics

Scope:

```text
analytics/
stream/stream-analytics.html
stream/stream-analytics.js
stream/stream-engagement-v2.js
```

Goal:

- Track real user-visible events:
  - `live_session_start`
  - `script_generated`
  - `news_alert_shown`
  - `quiz_started`
  - `quiz_completed`
  - `member_signup`
- Do not implement fake viewers, fake fans, fake comments, or fake engagement.

Verification:

```bash
cd /Users/rubykan/Documents/XAU
node --check stream/stream-analytics.js
node --check stream/stream-engagement-v2.js
```

### PR D: Avatar Integration

Scope:

```text
features/avatar-integration/
```

Goal:

- Avatar state API/client is explicit and optional.
- Missing avatar provider must not crash stream overlay.
- UI labels must say AI virtual presenter / AI presenter, not pretend to be a real human.

Verification:

```bash
cd /Users/rubykan/Documents/XAU
find features/avatar-integration -name "*.js" -maxdepth 3 -print -exec node --check {} \;
```

### PR E: Landing And Promo Assets

Scope:

```text
landing/
promo/README.md
promo/xau-poster-v1.html
promo/xau-reel-story-v1.html
```

Goal:

- Marketing assets are truthful and compliant.
- No fake testimonials, fake live numbers, or fake social proof.
- Clear risk disclaimer for XAU/trading content.

Verification:

```bash
cd /Users/rubykan/Documents/XAU
find landing promo -name "*.html" -maxdepth 3 -print
```

Manual:

```text
Open each HTML asset in browser
Check mobile layout
Check no broken local asset references
```

## Do Not Commit Yet

These paths should not be included until compared against merged `origin/main`:

```text
server/routes/tts.js
server/services/ttsService.js
```

Reason:

- Equivalent files were already added to merged PR #3.
- Local dirty versions may conflict with the tested merged implementation.

Suggested check:

```bash
cd /Users/rubykan/Documents/XAU
git fetch origin main
git diff --no-index server/routes/tts.js <(git show origin/main:server/routes/tts.js)
git diff --no-index server/services/ttsService.js <(git show origin/main:server/services/ttsService.js)
```

If shell process substitution is inconvenient, copy the `origin/main` versions to `/tmp` and diff there.

## Immediate Safe Action

Before another AI starts committing XAU work:

```bash
cd /Users/rubykan/Documents/XAU
git fetch origin main
git status --short
git diff --stat
```

Then create one branch per PR group:

```bash
git switch -c codex/xau-obs-overlay-v2
```

or use a worktree:

```bash
git worktree add /tmp/xau-obs-overlay-v2 origin/main
```

