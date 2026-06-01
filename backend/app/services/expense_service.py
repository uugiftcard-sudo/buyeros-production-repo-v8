"""Expense claims service — SQLite-backed.

Manages buyer expense/reimbursement claims:
  - submit: create a new pending claim
  - list_claims: query by status / buyer_name
  - get_claim: fetch single claim by id
  - update_status: approve / reject with reviewer note
  - export_csv: export all (or filtered) claims as CSV string
"""

from __future__ import annotations

import csv
import io
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# DB lives next to the backend package so it is gitignored via data/
_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "expenses.db"

VALID_STATUSES = {"pending", "approved", "rejected"}
VALID_CATEGORIES = {
    "travel",
    "accommodation",
    "meals",
    "shipping",
    "samples",
    "marketing",
    "office",
    "other",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ExpenseService:
    def __init__(self, db_path: Optional[str] = None) -> None:
        path = db_path or os.getenv("EXPENSE_DB_PATH") or str(_DEFAULT_DB_PATH)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = path
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expense_claims (
                    id            TEXT PRIMARY KEY,
                    buyer_name    TEXT NOT NULL,
                    amount        REAL NOT NULL,
                    currency      TEXT NOT NULL DEFAULT 'HKD',
                    category      TEXT NOT NULL DEFAULT 'other',
                    description   TEXT NOT NULL,
                    receipt_url   TEXT,
                    status        TEXT NOT NULL DEFAULT 'pending',
                    submitted_at  TEXT NOT NULL,
                    reviewed_at   TEXT,
                    reviewer_note TEXT,
                    reviewer      TEXT
                )
                """
            )
            conn.commit()
        logger.info("ExpenseService: DB ready at %s", self._db_path)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        buyer_name: str,
        amount: float,
        description: str,
        currency: str = "HKD",
        category: str = "other",
        receipt_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new expense claim with status=pending."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"invalid category '{category}'; valid: {sorted(VALID_CATEGORIES)}")
        if not buyer_name.strip():
            raise ValueError("buyer_name must not be empty")
        if not description.strip():
            raise ValueError("description must not be empty")

        claim_id = str(uuid.uuid4())
        now = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO expense_claims
                  (id, buyer_name, amount, currency, category,
                   description, receipt_url, status, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (claim_id, buyer_name.strip(), amount, currency.upper(),
                 category, description.strip(), receipt_url, now),
            )
            conn.commit()
        logger.info("ExpenseService: claim %s submitted by %s", claim_id, buyer_name)
        return self.get_claim(claim_id)  # type: ignore[return-value]

    def list_claims(
        self,
        status: Optional[str] = None,
        buyer_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return claims with optional filters."""
        conditions: List[str] = []
        params: List[Any] = []

        if status:
            if status not in VALID_STATUSES:
                raise ValueError(f"invalid status '{status}'")
            conditions.append("status = ?")
            params.append(status)
        if buyer_name:
            conditions.append("buyer_name LIKE ?")
            params.append(f"%{buyer_name}%")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params += [max(1, min(limit, 500)), max(0, offset)]

        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM expense_claims
                {where}
                ORDER BY submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM expense_claims WHERE id = ?", (claim_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def update_status(
        self,
        claim_id: str,
        new_status: str,
        reviewer: Optional[str] = None,
        reviewer_note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Approve or reject a claim. Returns updated claim or None if not found."""
        if new_status not in {"approved", "rejected"}:
            raise ValueError("new_status must be 'approved' or 'rejected'")
        now = _now_iso()
        with self._conn() as conn:
            result = conn.execute(
                """
                UPDATE expense_claims
                SET status = ?, reviewed_at = ?, reviewer = ?, reviewer_note = ?
                WHERE id = ?
                """,
                (new_status, now, reviewer, reviewer_note, claim_id),
            )
            conn.commit()
            if result.rowcount == 0:
                return None
        logger.info("ExpenseService: claim %s → %s by %s", claim_id, new_status, reviewer)
        return self.get_claim(claim_id)

    def export_csv(
        self,
        status: Optional[str] = None,
        buyer_name: Optional[str] = None,
    ) -> str:
        """Return all matching claims as a CSV string."""
        claims = self.list_claims(status=status, buyer_name=buyer_name, limit=5000)
        if not claims:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(claims[0].keys()))
        writer.writeheader()
        writer.writerows(claims)
        return buf.getvalue()
