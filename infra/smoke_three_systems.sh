#!/usr/bin/env bash
set -euo pipefail

echo "infra/smoke_three_systems.sh is kept for compatibility."
echo "Canonical smoke is now three lines: buyer_ai / commerce / xau."

exec "$(dirname "$0")/smoke_four_systems.sh" "$@"
