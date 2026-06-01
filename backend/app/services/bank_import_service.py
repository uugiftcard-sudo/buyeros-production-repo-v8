"""Bank import service with proper transaction handling."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class BankImportService:
    """Service for importing bank transactions with transaction safety."""

    def __init__(self) -> None:
        self._pending_imports: list[dict[str, Any]] = []

    def import_transactions(
        self,
        transactions: list[dict[str, Any]],
        atomic: bool = True,
    ) -> dict[str, Any]:
        """
        Import bank transactions with optional atomicity.
        
        Args:
            transactions: List of transaction dicts
            atomic: If True, all or nothing. If False, import individually.
        
        Returns:
            Import result with success count and IDs.
        """
        if not transactions:
            return {"imported": 0, "failed": 0, "transaction_ids": []}

        import_id = f"imp-{uuid.uuid4().hex[:12]}"
        transaction_ids: list[str] = []
        failed: list[str] = []

        if atomic:
            # Atomic import: all or nothing
            try:
                for tx in transactions:
                    tx_id = self._import_single_transaction(tx, import_id)
                    transaction_ids.append(tx_id)
                logger.info("Atomic import %s completed: %d transactions", import_id, len(transaction_ids))
                return {
                    "imported": len(transaction_ids),
                    "failed": 0,
                    "import_id": import_id,
                    "transaction_ids": transaction_ids,
                }
            except Exception as exc:
                logger.error("Atomic import %s failed: %s", import_id, exc)
                # Rollback: clear all pending imports
                self._rollback_import(import_id)
                return {
                    "imported": 0,
                    "failed": len(transactions),
                    "import_id": import_id,
                    "error": str(exc),
                }
        else:
            # Non-atomic: best effort
            for tx in transactions:
                try:
                    tx_id = self._import_single_transaction(tx, import_id)
                    transaction_ids.append(tx_id)
                except Exception as exc:
                    logger.warning("Transaction import failed: %s", exc)
                    failed.append(str(exc))
            
            return {
                "imported": len(transaction_ids),
                "failed": len(failed),
                "import_id": import_id,
                "transaction_ids": transaction_ids,
                "errors": failed[:10],  # Limit error list
            }

    def _import_single_transaction(
        self,
        transaction: dict[str, Any],
        import_id: str,
    ) -> str:
        """Import a single transaction with validation."""
        tx_id = f"tx-{uuid.uuid4().hex[:12]}"
        
        # Validate required fields
        required = ["date", "amount", "description"]
        for field in required:
            if field not in transaction:
                raise ValueError(f"Missing required field: {field}")
        
        # Store transaction
        record = {
            "tx_id": tx_id,
            "import_id": import_id,
            "date": transaction.get("date"),
            "amount": float(transaction.get("amount", 0)),
            "description": str(transaction.get("description", "")),
            "reference": transaction.get("reference", ""),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._pending_imports.append(record)
        
        return tx_id

    def _rollback_import(self, import_id: str) -> None:
        """Rollback all transactions from an import."""
        self._pending_imports = [
            tx for tx in self._pending_imports
            if tx.get("import_id") != import_id
        ]
        logger.info("Rolled back import: %s", import_id)

    def get_pending_imports(self) -> list[dict[str, Any]]:
        """Get all pending imports."""
        return self._pending_imports.copy()

    def reconcile(
        self,
        transaction_ids: list[str],
        match_ids: list[str],
    ) -> dict[str, Any]:
        """Match transactions with source records."""
        matched = 0
        for tx_id, match_id in zip(transaction_ids, match_ids):
            for tx in self._pending_imports:
                if tx["tx_id"] == tx_id:
                    tx["matched_with"] = match_id
                    tx["status"] = "matched"
                    matched += 1
                    break
        return {"matched": matched, "total": len(transaction_ids)}
