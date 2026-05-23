"""Canonical workspace/lane normalization helpers."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


CANONICAL_WORKSPACES: Tuple[str, ...] = ("buyeros", "cloth", "xau")
CANONICAL_WORKSPACE_SET = set(CANONICAL_WORKSPACES)

WORKSPACE_ALIASES: Dict[str, str] = {
    "buyeros": "buyeros",
    "ai_team": "buyeros",
    "ai-team": "buyeros",
    "ai_solo_team": "buyeros",
    "ai-solo-team": "buyeros",
    "cloth": "cloth",
    "commerce": "cloth",
    "report": "cloth",
    "shop": "cloth",
    "reporting": "cloth",
    "order": "cloth",
    "orders": "cloth",
    "xau": "xau",
    "xau-team": "xau",
    "xau_team": "xau",
    "xau_promo": "xau",
    "xaupromo": "xau",
    "xau-promo": "xau",
    "promo": "xau",
}


def normalize_workspace(value: str | None) -> str:
    """Normalize a workspace/lane value to canonical `buyeros|cloth|xau`.

    Unknown values fallback to `buyeros` for backward compatibility to avoid
    surprising 4xx from strict normalization during legacy data migration.
    """

    raw = (value or "").strip()
    if not raw:
        return "buyeros"
    return WORKSPACE_ALIASES.get(raw, raw if raw in CANONICAL_WORKSPACE_SET else "buyeros")


def normalize_many(values: Iterable[str | None]) -> Dict[str, str]:
    """Normalize multiple values and return string(original)->normalized mapping."""

    return {value or "": normalize_workspace(value) for value in values}
