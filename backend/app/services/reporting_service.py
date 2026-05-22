"""Report products for BuyerOS operations."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..memory_store import MemoryStore


class ReportingService:
    """Build persistent report snapshots from shared BuyerOS memory."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def create_report(self, *, period: str = "daily", date: Optional[str] = None) -> Dict[str, Any]:
        report_date = date or datetime.now(timezone.utc).date().isoformat()
        refunds = self.memory.search_memory(namespace_prefix=("buyeros", "refunds"), limit=100)
        orders = self.memory.search_memory(namespace_prefix=("buyeros", "orders"), limit=100)
        finance = self.memory.search_memory(namespace_prefix=("buyeros", "finance"), limit=100)
        alerts = self.memory.search_memory(namespace_prefix=("buyeros", "alerts"), limit=100)
        ocr_entries = self.memory.search_memory(namespace_prefix=("buyeros", "ocr_entries"), limit=100)
        report_id = f"{period}-{report_date}"
        data = {
            "report_id": report_id,
            "project_id": "cloth",
            "project": "cloth",
            "period": period,
            "date": report_date,
            "summary": f"{report_date} {period}：訂單 {len(orders)}，退款 {len(refunds)}，OCR {len(ocr_entries)}，告警 {len(alerts)}。",
            "counts": {
                "orders": len(orders),
                "refunds": len(refunds),
                "finance": len(finance),
                "alerts": len(alerts),
                "ocr_entries": len(ocr_entries),
            },
            "sections": {
                "refunds": self._compact(refunds),
                "orders": self._compact(orders),
                "finance": self._compact(finance),
                "alerts": self._compact(alerts),
                "ocr_entries": self._compact(ocr_entries),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "reports"], report_id, data, created_by="reporting_service")
        return {"ok": True, "report": data}

    def history(self, *, limit: int = 20) -> Dict[str, Any]:
        reports = self.memory.search_memory(namespace_prefix=("buyeros", "reports"), limit=limit)
        return {"ok": True, "items": reports}

    def export_csv(self, *, report_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        reports = (
            self.memory.search_memory(namespace_prefix=("buyeros", "reports"), memory_key=report_id, limit=1)
            if report_id
            else self.memory.search_memory(namespace_prefix=("buyeros", "reports"), limit=limit)
        )
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["report_id", "period", "date", "summary", "orders", "refunds", "alerts"])
        writer.writeheader()
        for entry in reports:
            content = entry.get("content") or {}
            counts = content.get("counts") or {}
            writer.writerow(
                {
                    "report_id": content.get("report_id") or entry.get("memory_key"),
                    "period": content.get("period", ""),
                    "date": content.get("date", ""),
                    "summary": content.get("summary", ""),
                    "orders": counts.get("orders", 0),
                    "refunds": counts.get("refunds", 0),
                    "alerts": counts.get("alerts", 0),
                }
            )
        return {"ok": True, "format": "csv", "content": output.getvalue()}

    def _compact(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compacted: List[Dict[str, Any]] = []
        for item in items[:10]:
            content = item.get("content") or {}
            compacted.append(
                {
                    "key": item.get("memory_key"),
                    "summary": content.get("summary") or content.get("result") or content.get("status") or str(content)[:180],
                    "created_at": item.get("created_at"),
                }
            )
        return compacted
