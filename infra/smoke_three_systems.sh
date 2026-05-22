#!/usr/bin/env bash
set -euo pipefail

echo "infra/smoke_three_systems.sh is kept for compatibility."
echo "Canonical smoke is now three workspaces: BuyerOS Core / CLOTH / XAU."

exec "$(dirname "$0")/smoke_four_systems.sh" "$@"
