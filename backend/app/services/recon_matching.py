"""Simple deterministic item matching for recon comparisons.

MVP strategy (Option A):
- Normalize item names (lowercase, strip punctuation/whitespace)
- Similarity score via stdlib difflib.SequenceMatcher
- Greedy match: for each scanned item, pick best unmatched declared item above threshold

Outputs:
- matched pairs
- missing_declared (declared but not matched)
- undeclared_scanned (scanned but not matched)
- totals + risk flags
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


def _normalize_name(value: str) -> str:
    s = (value or "").lower().strip()
    # Keep alnum + basic CJK; drop punctuation/symbols
    s = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def similarity(a: str, b: str) -> float:
    a_n = _normalize_name(a)
    b_n = _normalize_name(b)
    if not a_n or not b_n:
        return 0.0
    return float(SequenceMatcher(None, a_n, b_n).ratio())


@dataclass
class MatchResult:
    score: float
    scanned_index: int
    declared_index: int


def match_items(
    *,
    declared: List[Dict[str, Any]],
    scanned: List[Dict[str, Any]],
    threshold: float = 0.72,
) -> Dict[str, Any]:
    # Precompute similarity matrix
    candidates: List[MatchResult] = []
    for si, s in enumerate(scanned):
        for di, d in enumerate(declared):
            score = similarity(str(s.get("item_name", "")), str(d.get("item_name", "")))
            if score >= threshold:
                candidates.append(MatchResult(score=score, scanned_index=si, declared_index=di))

    # Greedy: highest score first
    candidates.sort(key=lambda x: x.score, reverse=True)

    used_scanned = set()
    used_declared = set()
    matches: List[Dict[str, Any]] = []

    for c in candidates:
        if c.scanned_index in used_scanned or c.declared_index in used_declared:
            continue
        s = scanned[c.scanned_index]
        d = declared[c.declared_index]
        used_scanned.add(c.scanned_index)
        used_declared.add(c.declared_index)

        qty_decl = int(d.get("quantity") or 1)
        qty_scan = int(s.get("quantity") or 1)
        unit_decl = d.get("unit_price_hkd")
        unit_scan = s.get("unit_price_hkd")
        sub_decl = d.get("subtotal_hkd")
        sub_scan = s.get("subtotal_hkd")

        matches.append(
            {
                "score": c.score,
                "declared": d,
                "scanned": s,
                "quantity_mismatch": qty_decl != qty_scan,
                "price_mismatch": (unit_decl is not None and unit_scan is not None and int(unit_decl) != int(unit_scan)),
                "subtotal_mismatch": (sub_decl is not None and sub_scan is not None and int(sub_decl) != int(sub_scan)),
            }
        )

    missing_declared = [d for i, d in enumerate(declared) if i not in used_declared]
    undeclared_scanned = [s for i, s in enumerate(scanned) if i not in used_scanned]

    mismatched = [m for m in matches if m["quantity_mismatch"] or m["price_mismatch"] or m["subtotal_mismatch"]]

    return {
        "matches": matches,
        "missing_declared": missing_declared,
        "undeclared_scanned": undeclared_scanned,
        "mismatched": mismatched,
        "stats": {
            "declared_count": len(declared),
            "scanned_count": len(scanned),
            "matched_count": len(matches),
            "mismatched_count": len(mismatched),
            "missing_declared_count": len(missing_declared),
            "undeclared_scanned_count": len(undeclared_scanned),
        },
    }
