"""Business automation workflows for BuyerOS operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from ..memory_store import MemoryStore


@dataclass
class AutomationResult:
    ok: bool
    workflow: str
    status: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "workflow": self.workflow,
            "status": self.status,
            "message": self.message,
            "data": self.data,
        }


class BusinessAutomationService:
    """Small deterministic workflows used by cron, UI, and Telegram ops."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def create_daily_report(self, *, date: Optional[str] = None) -> Dict[str, Any]:
        report_date = date or datetime.now(timezone.utc).date().isoformat()
        refunds = self.memory.search_memory(namespace_prefix=("buyeros", "refunds"), limit=100)
        finance = self.memory.search_memory(namespace_prefix=("buyeros", "finance"), limit=20)
        orders = self.memory.search_memory(namespace_prefix=("buyeros", "orders"), limit=100)
        alerts = self.memory.search_memory(namespace_prefix=("buyeros", "alerts"), limit=20)
        summary = (
            f"{report_date} 日報：訂單 {len(orders)}，退款 {len(refunds)}，"
            f"財務記錄 {len(finance)}，告警 {len(alerts)}。"
        )
        payload = {
            "date": report_date,
            "summary": summary,
            "counts": {
                "orders": len(orders),
                "refunds": len(refunds),
                "finance": len(finance),
                "alerts": len(alerts),
            },
        }
        self.memory.save_memory(["buyeros", "reports"], report_date, payload, created_by="business_automation")
        return AutomationResult(True, "daily_report", "completed", summary, payload).to_dict()

    def post_ocr_entry(self, *, text: str, source: str = "manual", entry_id: Optional[str] = None) -> Dict[str, Any]:
        key = entry_id or f"ocr-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        amount = self._extract_amount(text)
        status = "needs_review" if amount is None else "posted"
        payload = {
            "entry_id": key,
            "source": source,
            "text": text,
            "amount_hkd": amount,
            "status": status,
        }
        self.memory.save_memory(["buyeros", "ocr_entries"], key, payload, created_by="business_automation")
        message = "OCR 入帳已建立，等待人工覆核。" if status == "needs_review" else f"OCR 入帳 HKD {amount:.2f} 已建立。"
        return AutomationResult(True, "ocr_posting", status, message, payload).to_dict()

    def reconcile_entries(self, *, expected_total: float, actual_total: float, reference: str = "manual") -> Dict[str, Any]:
        difference = round(actual_total - expected_total, 2)
        status = "matched" if difference == 0 else "mismatch"
        payload = {
            "reference": reference,
            "expected_total": expected_total,
            "actual_total": actual_total,
            "difference": difference,
            "status": status,
        }
        self.memory.save_memory(["buyeros", "reconciliation"], reference, payload, created_by="business_automation")
        if status == "mismatch":
            self.memory.save_memory(["buyeros", "alerts"], reference, payload, created_by="business_automation")
        message = "對帳完成，金額一致。" if status == "matched" else f"對帳差異 HKD {difference:.2f}，已建立告警。"
        return AutomationResult(True, "reconciliation", status, message, payload).to_dict()

    def generate_alerts(self, *, items: Iterable[Dict[str, Any]], threshold: float = 0) -> Dict[str, Any]:
        alerts: List[Dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            amount = float(item.get("amount", 0) or 0)
            if amount > threshold:
                alert = {"index": index, **item, "threshold": threshold, "status": "open"}
                alerts.append(alert)
                self.memory.save_memory(
                    ["buyeros", "alerts"],
                    str(item.get("id") or f"alert-{index}"),
                    alert,
                    created_by="business_automation",
                )
        return AutomationResult(
            True,
            "alerts",
            "completed",
            f"已建立 {len(alerts)} 個異常告警。",
            {"alerts": alerts, "threshold": threshold},
        ).to_dict()

    def request_approval(self, *, task_id: str, reason: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        content = {"task_id": task_id, "reason": reason, "payload": payload or {}, "status": "pending"}
        self.memory.save_memory(["buyeros", "approvals"], task_id, content, created_by="business_automation")
        return AutomationResult(True, "approval", "pending", "已建立人工覆核任務。", content).to_dict()

    def record_retry(self, *, task_id: str, error: str, attempt: int) -> Dict[str, Any]:
        status = "retry_scheduled" if attempt < 3 else "failed"
        content = {"task_id": task_id, "error": error, "attempt": attempt, "status": status}
        self.memory.save_memory(["buyeros", "retries"], task_id, content, created_by="business_automation")
        return AutomationResult(True, "retry", status, f"任務 {task_id} {status}。", content).to_dict()

    def _extract_amount(self, text: str) -> Optional[float]:
        import re

        match = re.search(r"(?:HKD|港幣|\$)\s*([0-9]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if not match:
            return None
        return float(match.group(1))
