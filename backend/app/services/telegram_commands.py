"""Telegram command parsing for BuyerOS.

We keep Telegram UX deterministic and terse:
- /start - Welcome message
- /status - Quick status: today's declarations, bank imports, reconciliations
- /recon [date] - Trigger reconciliation for a date
- /bank_import <bank_code> <account_id> - Trigger bank import
- /help - List all commands
- /scan <image_url> buyer=<id> team=<id?> decl=<id?> date=<YYYY-MM-DD?>
- /compare decl=<id> scan=<id> buyer=<id> team=<id?> threshold=<0.50-0.95?> date=<YYYY-MM-DD?>
- /refundcard return=<id> last4=<1234> buyer=<id?> team=<id?>

The parser returns a tuple: (command, args_dict)
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


def _parse_kv_pairs(text: str) -> Dict[str, str]:
    # key=value pairs separated by spaces. Values may be quoted.
    pattern = re.compile(r"(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)=(?P<val>\"[^\"]+\"|'[^']+'|\S+)")
    out: Dict[str, str] = {}
    for m in pattern.finditer(text):
        key = m.group("key").strip().lower()
        val = m.group("val").strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        out[key] = val
    return out


def parse_telegram_command(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None

    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower().lstrip("/")
    rest = parts[1] if len(parts) > 1 else ""
    kv = _parse_kv_pairs(rest)

    # Support first positional arg (usually url)
    first_token = ""
    if rest:
        # remove kv pairs from rest to get remaining tokens
        rest_wo_kv = re.sub(r"\b[a-zA-Z_][a-zA-Z0-9_]*=(\"[^\"]+\"|'[^']+'|\S+)", " ", rest)
        rest_wo_kv = re.sub(r"\s+", " ", rest_wo_kv).strip()
        first_token = rest_wo_kv.split(" ", 1)[0] if rest_wo_kv else ""

    if cmd in ["start", "welcome"]:
        return ("start", {})

    if cmd in ["status", "stat"]:
        return ("status", {})

    if cmd in ["recon", "reconciliation"]:
        # /recon [date] — date is first positional arg or date=kv
        date_val = first_token or kv.get("date") or ""
        return ("recon", {"date": date_val})

    if cmd in ["bank_import", "bankimport", "bank"]:
        # /bank_import <bank_code> <account_id> — positional
        tokens = rest.split()
        bank_code = tokens[0] if len(tokens) > 0 else ""
        account_id = tokens[1] if len(tokens) > 1 else ""
        return ("bank_import", {
            "bank_code": bank_code,
            "account_id": account_id,
        })

    if cmd in ["help", "?"]:
        return ("help", {})

    if cmd in ["scan", "receipt", "reconscan"]:
        image_url = kv.get("url") or first_token
        args = {
            "image_url": image_url,
            "buyer_id": kv.get("buyer") or kv.get("buyer_id") or "",
            "team_id": kv.get("team") or kv.get("team_id"),
            "declaration_id": kv.get("decl") or kv.get("declaration") or kv.get("declaration_id"),
            "scan_id": kv.get("scan_id"),
            "date": kv.get("date"),
        }
        return ("scan", args)

    if cmd in ["compare", "reconcompare"]:
        args = {
            "declaration_id": kv.get("decl") or kv.get("declaration") or kv.get("declaration_id") or "",
            "scan_id": kv.get("scan") or kv.get("scan_id") or "",
            "buyer_id": kv.get("buyer") or kv.get("buyer_id") or "",
            "team_id": kv.get("team") or kv.get("team_id"),
            "threshold": kv.get("threshold"),
            "date": kv.get("date"),
        }
        return ("compare", args)

    if cmd in ["refundcard", "card", "verifycard"]:
        args = {
            "return_id": kv.get("return") or kv.get("return_id") or "",
            "refund_card_last4": kv.get("last4") or kv.get("refund_card_last4") or "",
            "buyer_id": kv.get("buyer") or kv.get("buyer_id"),
            "team_id": kv.get("team") or kv.get("team_id"),
        }
        return ("refundcard", args)

    return None
