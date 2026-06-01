from __future__ import annotations

import re
import sys
from pathlib import Path


def _load_env_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding="utf-8").splitlines()


def _parse_env(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        values[key] = value
    return values


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--env":
        print("Usage: python backend/scripts/validate_env.py --env <env_file>")
        return 2

    env_path = Path(argv[2]).expanduser().resolve()
    values = _parse_env(_load_env_lines(env_path))

    required = [
        "PUBLIC_BASE_URL",
        "BUYEROS_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET",
        "REDIS_URL",
        "OPENROUTER_API_KEY",
        "BUYEROS_DOMAIN",
    ]

    missing = [key for key in required if not values.get(key)]
    if missing:
        print("Missing required env vars:")
        for key in missing:
            print(f"- {key}")
        return 1

    base_url = values.get("PUBLIC_BASE_URL", "")
    if not re.match(r"^https?://", base_url):
        print("PUBLIC_BASE_URL must start with http:// or https://")
        return 1

    print("Env OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
