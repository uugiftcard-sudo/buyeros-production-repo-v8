"""Validate BuyerOS production env files."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_KEYS = [
    "PUBLIC_BASE_URL",
    "BUYEROS_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "REDIS_URL",
    "OPENROUTER_API_KEY",
]

PLACEHOLDER_BITS = ["CHANGE_ME", "YOUR_DOMAIN", "YOUR_", "root@YOUR", "TODO_"]


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python backend/scripts/validate_env.py <env_file>")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Missing env file: {path}")
        return 2
    values = parse_env(path)
    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    placeholders = [
        key
        for key, value in values.items()
        if any(bit in value for bit in PLACEHOLDER_BITS)
    ]
    if missing:
        print("Missing required keys:")
        for key in missing:
            print(f"- {key}")
    if placeholders:
        print("Placeholder values still present:")
        for key in placeholders:
            print(f"- {key}")
    if missing or placeholders:
        return 1
    print("Env file looks ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
