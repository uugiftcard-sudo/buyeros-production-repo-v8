"""HSBC HK CSV parser.

Based on sample screenshot:
- Delimiter: comma
- Headers include: Value Date, Transaction Date, Description, Debit, Credit, Balance
- Date format: DD/MM/YYYY
- Debit/Credit columns are mutually exclusive

We convert amounts into minor units:
- HKD/GBP -> cents
- USDT -> micro units (1e-6)
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import List, Optional

from .base import BankParseResult, BankTransactionRow


def _parse_date_ddmmyyyy(value: str) -> Optional[str]:
    s = (value or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y").date().isoformat()
    except Exception:
        return None


def _to_minor(value: str, *, currency: str) -> Optional[int]:
    s = (value or "").strip()
    if not s:
        return None
    # strip commas
    s = s.replace(",", "")
    # remove non numeric/dot/minus
    s = re.sub(r"[^0-9\.\-]", "", s)
    if not s:
        return None
    try:
        v = float(s)
        if currency.upper() == "USDT":
            return int(round(v * 1_000_000))
        return int(round(v * 100))
    except Exception:
        return None


class HsbcHkCsvParser:
    bank_code = "hsbc_hk"

    def parse(self, *, content: str, account_id: str, currency: str) -> BankParseResult:
        errors: List[str] = []
        txs: List[BankTransactionRow] = []

        reader = csv.DictReader(io.StringIO(content), delimiter=",")
        if not reader.fieldnames:
            return BankParseResult(False, self.bank_code, account_id, currency, [], ["missing_header"])

        # Normalize header map
        header_map = {h.lower().strip(): h for h in reader.fieldnames}
        col_value_date = header_map.get("value date")
        col_tx_date = header_map.get("transaction date")
        col_desc = header_map.get("description")
        col_debit = header_map.get("debit")
        col_credit = header_map.get("credit")
        col_balance = header_map.get("balance")

        if not col_value_date or not col_desc or (not col_debit and not col_credit):
            return BankParseResult(
                False,
                self.bank_code,
                account_id,
                currency,
                [],
                ["missing_required_columns:value date/description/(debit|credit)"],
            )

        for line_no, row in enumerate(reader, start=2):
            d = _parse_date_ddmmyyyy(str(row.get(col_value_date, "")))
            if not d and col_tx_date:
                d = _parse_date_ddmmyyyy(str(row.get(col_tx_date, "")))
            desc = str(row.get(col_desc, "") or "").strip() or "(no description)"

            debit_minor = _to_minor(str(row.get(col_debit, ""))) if col_debit else None
            credit_minor = _to_minor(str(row.get(col_credit, ""))) if col_credit else None
            bal_minor = _to_minor(str(row.get(col_balance, "")), currency=currency) if col_balance else None

            amount_minor: Optional[int] = None
            if debit_minor is not None and debit_minor != 0:
                amount_minor = -abs(debit_minor)
            elif credit_minor is not None and credit_minor != 0:
                amount_minor = abs(credit_minor)

            if not d or amount_minor is None:
                errors.append(f"row_{line_no}_parse_failed")
                continue

            txs.append(
                BankTransactionRow(
                    date=d,
                    description=desc[:500],
                    amount=amount_minor,
                    currency=currency.upper(),
                    balance=bal_minor,
                )
            )

        ok = bool(txs)
        return BankParseResult(ok, self.bank_code, account_id, currency.upper(), txs, errors)
