"""Canonical workspace/lane normalization helpers."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


CANONICAL_WORKSPACES: Tuple[str, ...] = ("buyer_ai", "commerce", "xau")
CANONICAL_WORKSPACE_SET = set(CANONICAL_WORKSPACES)

WORKSPACE_ALIASES: Dict[str, str] = {
    "buyer_ai": "buyer_ai",
    "buyeros": "buyer_ai",
    "ai_team": "buyer_ai",
    "ai-team": "buyer_ai",
    "ai_solo_team": "buyer_ai",
    "ai-solo-team": "buyer_ai",
    "buyer_report": "buyer_ai",
    "buyer-report": "buyer_ai",
    "report": "buyer_ai",
    "reporting": "buyer_ai",
    "commerce": "commerce",
    "cloth": "commerce",
    "shop": "commerce",
    "order": "commerce",
    "orders": "commerce",
    "xau": "xau",
    "xau-team": "xau",
    "xau_team": "xau",
    "xau_promo": "xau",
    "xaupromo": "xau",
    "xau-promo": "xau",
    "promo": "xau",
}


def normalize_workspace(value: str | None) -> str:
    """Normalize a workspace/lane value to canonical `buyer_ai|commerce|xau`.

    Unknown values fallback to `buyer_ai` for backward compatibility to avoid
    surprising 4xx from strict normalization during legacy data migration.
    """

    raw = (value or "").strip()
    if not raw:
        return "buyer_ai"
    return WORKSPACE_ALIASES.get(raw, raw if raw in CANONICAL_WORKSPACE_SET else "buyer_ai")


def normalize_many(values: Iterable[str | None]) -> Dict[str, str]:
    """Normalize multiple values and return string(original)->normalized mapping."""

    return {value or "": normalize_workspace(value) for value in values}
