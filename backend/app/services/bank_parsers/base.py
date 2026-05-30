"""Bank CSV parsing framework.

We support multiple bank formats by registering parsers keyed by bank_code.
Parsers should be deterministic (no AI calls).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Protocol, Literal


CurrencyCode = Literal["HKD", "GBP", "USDT"]


@dataclass
class BankTransactionRow:
    date: str  # YYYY-MM-DD
    description: str
    amount: int  # minor units (HKD/GBP cents; USDT micro)
    currency: CurrencyCode
    balance: Optional[int] = None
    reference: Optional[str] = None


@dataclass
class BankParseResult:
    ok: bool
    bank_code: str
    account_id: str
    currency: CurrencyCode
    transactions: List[BankTransactionRow]
    errors: List[str]


class BankCsvParser(Protocol):
    bank_code: str

    def parse(self, *, content: str, account_id: str, currency: str) -> BankParseResult: ...


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: Dict[str, BankCsvParser] = {}

    def register(self, parser: BankCsvParser) -> None:
        self._parsers[parser.bank_code.lower().strip()] = parser

    def get(self, bank_code: str) -> Optional[BankCsvParser]:
        return self._parsers.get(bank_code.lower().strip())

    def has(self, bank_code: str) -> bool:
        return self.get(bank_code) is not None

    def list_codes(self) -> List[str]:
        return sorted(self._parsers.keys())
