"""Generic CSV parser.

This is a best-effort parser for simple CSV exports that contain:
- date
- description
- amount
Optionally balance.

It is designed as a fallback until bank-specific parsers are added.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import List, Optional

from .base import BankParseResult, BankTransactionRow


def _detect_delimiter(sample: str) -> str:
    # Quick heuristic: prefer comma, then semicolon, then tab
    for d in [",", ";", "\t"]:
        if sample.count(d) >= 2:
            return d
    return ","


def _parse_date(value: str) -> Optional[str]:
    s = (value or "").strip()
    if not s:
        return None
    # Common formats
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d"]:
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except Exception:
            pass
    return None


def _parse_amount_minor(value: str, *, currency: str) -> Optional[int]:
    s = (value or "").strip()
    if not s:
        return None
    # Handle parentheses negatives: (1,234.56)
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()

    # remove currency symbols and spaces
    s = re.sub(r"[^0-9,\.\-]", "", s)
    s = s.replace(",", "")
    if not s:
        return None

    try:
        if currency.upper() == "USDT":
            # keep 6 decimals (micro-units) for now; store as 1e-6
            val = float(s)
            minor = int(round(val * 1_000_000))
        else:
            val = float(s)
            minor = int(round(val * 100))
        return -minor if neg or s.startswith("-") else minor
    except Exception:
        return None


class GenericCsvParser:
    bank_code = "generic"

    def parse(self, *, content: str, account_id: str, currency: str) -> BankParseResult:
        errors: List[str] = []
        transactions: List[BankTransactionRow] = []

        sample = content[:2048]
        delimiter = _detect_delimiter(sample)

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        if not reader.fieldnames:
            return BankParseResult(False, self.bank_code, account_id, currency, [], ["missing_header"])

        # map columns
        fields = [f.lower().strip() for f in reader.fieldnames]
        def _pick(*cands: str) -> Optional[str]:
            for c in cands:
                if c in fields:
                    return reader.fieldnames[fields.index(c)]
            return None

        col_date = _pick("date", "transaction date", "posting date", "日期", "交易日期")
        col_desc = _pick("description", "details", "narrative", "備註", "描述")
        col_amount = _pick("amount", "transaction amount", "金額", "交易金額")
        col_balance = _pick("balance", "餘額", "結餘")

        if not col_date or not col_amount:
            missing = [x for x in ["date" if not col_date else None, "amount" if not col_amount else None] if x]
            return BankParseResult(False, self.bank_code, account_id, currency, [], [f"missing_columns:{','.join(missing)}"])

        for i, row in enumerate(reader, start=2):
            d = _parse_date(str(row.get(col_date, "")))
            amt = _parse_amount_minor(str(row.get(col_amount, "")), currency=currency)
            desc = str(row.get(col_desc, "") if col_desc else "").strip() or "(no description)"
            bal = _parse_amount_minor(str(row.get(col_balance, "")), currency=currency) if col_balance else None
            if not d or amt is None:
                errors.append(f"row_{i}_parse_failed")
                continue
            transactions.append(
                BankTransactionRow(
                    date=d,
                    description=desc[:500],
                    amount=amt,
                    currency=currency.upper(),
                    balance=bal,
                )
            )

        ok = bool(transactions)
        return BankParseResult(ok, self.bank_code, account_id, currency.upper(), transactions, errors)
