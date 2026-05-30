"""Manual bank import helpers.

We accept major-unit amounts from UI/ops copy-paste:
- HKD/GBP: two decimals -> cents
- USDT: up to 6 decimals -> micro units
"""

from __future__ import annotations

import re
from typing import Optional


def major_to_minor(value: float, *, currency: str) -> int:
    cur = (currency or "").upper().strip()
    if cur == "USDT":
        return int(round(float(value) * 1_000_000))
    return int(round(float(value) * 100))


def parse_major_amount(text: str, *, currency: str) -> Optional[float]:
    s = (text or "").strip()
    if not s:
        return None
    # strip non numeric/dot/minus/commas/parentheses
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()
    s = re.sub(r"[^0-9,\.\-]", "", s)
    s = s.replace(",", "")
    if not s:
        return None
    try:
        v = float(s)
        if neg:
            v = -abs(v)
        return v
    except Exception:
        return None
