"""Business automation workflows for BuyerOS operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, Iterable, List, Optional

from .ocr_service import OCRService

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

    def __init__(self, memory_store: MemoryStore, *, orders_service: Any = None, ocr_service: Optional[OCRService] = None) -> None:
        self.memory = memory_store
        self.orders_service = orders_service
        self.ocr_service = ocr_service or OCRService()

    def create_daily_report(self, *, date: Optional[str] = None) -> Dict[str, Any]:
        report_date = date or datetime.now(timezone.utc).date().isoformat()
        refunds = self.memory.search_memory(namespace_prefix=("buyeros", "refunds"), limit=100)
        finance = self.memory.search_memory(namespace_prefix=("buyeros", "finance"), limit=20)
        orders = self.memory.search_memory(namespace_prefix=("buyeros", "orders"), limit=100)
        alerts = self.memory.search_memory(namespace_prefix=("buyeros", "alerts"), limit=20)
        ocr_entries = self.memory.search_memory(namespace_prefix=("buyeros", "ocr_entries"), limit=100)
        reconciliation = self.memory.search_memory(namespace_prefix=("buyeros", "reconciliation"), limit=100)
        approvals = self.memory.search_memory(namespace_prefix=("buyeros", "approvals"), limit=100)
        retries = self.memory.search_memory(namespace_prefix=("buyeros", "retries"), limit=100)
        summary = (
            f"{report_date} 日報：訂單 {len(orders)}，退款 {len(refunds)}，"
            f"財務記錄 {len(finance)}，OCR {len(ocr_entries)}，告警 {len(alerts)}，"
            f"覆核 {len(approvals)}，重試 {len(retries)}。"
        )
        payload = {
            "project_id": "cloth",
            "date": report_date,
            "summary": summary,
            "counts": {
                "orders": len(orders),
                "refunds": len(refunds),
                "finance": len(finance),
                "alerts": len(alerts),
                "ocr_entries": len(ocr_entries),
                "reconciliation": len(reconciliation),
                "approvals": len(approvals),
                "retries": len(retries),
            },
        }
        self.memory.save_memory(["buyeros", "reports"], report_date, payload, created_by="business_automation")
        return AutomationResult(True, "daily_report", "completed", summary, payload).to_dict()

    def post_ocr_entry(self, *, text: str, source: str = "manual", entry_id: Optional[str] = None) -> Dict[str, Any]:
        key = entry_id or f"ocr-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        amount = self._extract_amount(text)
        status = "needs_review" if amount is None else "posted"
        payload = {
            "project_id": "cloth",
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
            "project_id": "cloth",
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
                alert = {"project_id": "cloth", "index": index, **item, "threshold": threshold, "status": "open"}
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
        content = {"project_id": "cloth", "task_id": task_id, "reason": reason, "payload": payload or {}, "status": "pending"}
        self.memory.save_memory(["buyeros", "approvals"], task_id, content, created_by="business_automation")
        return AutomationResult(True, "approval", "pending", "已建立人工覆核任務。", content).to_dict()

    def record_retry(self, *, task_id: str, error: str, attempt: int) -> Dict[str, Any]:
        status = "retry_scheduled" if attempt < 3 else "failed"
        content = {"project_id": "cloth", "task_id": task_id, "error": error, "attempt": attempt, "status": status}
        self.memory.save_memory(["buyeros", "retries"], task_id, content, created_by="business_automation")
        return AutomationResult(True, "retry", status, f"任務 {task_id} {status}。", content).to_dict()

    def close_cycle(
        self,
        *,
        ocr_text: str,
        expected_total: Optional[float],
        actual_total: Optional[float],
        order_id: Optional[str] = None,
        image_url: Optional[str] = None,
        ocr_language: str = "eng",
        reference: str = "close-cycle",
        source: str = "api",
        retry_error: Optional[str] = None,
        retry_attempt: int = 1,
        high_risk: bool = False,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        cycle_id = f"cycle-{uuid4().hex[:8]}"
        steps: List[Dict[str, Any]] = []
        order: Optional[Dict[str, Any]] = None
        order_total: Optional[float] = None
        ocr_provider_result: Optional[Dict[str, Any]] = None
        review_reasons: List[str] = []

        if order_id:
            order = self._get_order(order_id)
            if order and not order.get("error"):
                order_total = self._extract_order_total(order)
                self.memory.save_memory(["buyeros", "orders"], order_id, {"project_id": "cloth", **order}, created_by="business_automation")
                if order_total is not None:
                    expected_total = order_total
                else:
                    review_reasons.append("訂單未能抽出總額")
            else:
                review_reasons.append("訂單服務未能返回有效資料")

        if image_url:
            try:
                ocr_provider_result = self.ocr_service.extract_text(image_url=image_url, language=ocr_language)
            except Exception as exc:
                ocr_provider_result = {"ok": "false", "text": f"OCR 服務錯誤：{exc}", "provider": "ocr_space", "error": str(exc)}
            ocr_text = ocr_provider_result.get("text") or ocr_text
            extracted_actual = self._extract_amount(ocr_text)
            if extracted_actual is not None:
                actual_total = extracted_actual
            else:
                review_reasons.append("OCR 未能抽出實付金額")

        if expected_total is None:
            expected_total = 0
            review_reasons.append("缺少 expected_total")
        if actual_total is None:
            actual_total = 0
            review_reasons.append("缺少 actual_total")

        ocr = self.post_ocr_entry(text=ocr_text, source=source, entry_id=f"{cycle_id}-ocr")
        steps.append(ocr)

        approval: Optional[Dict[str, Any]] = None
        if ocr["status"] == "needs_review" or high_risk or review_reasons:
            approval = self.request_approval(
                task_id=f"{cycle_id}-approval",
                reason="；".join(review_reasons) if review_reasons else "OCR 無法抽出金額或命中高風險條件",
                payload={
                    "cycle_id": cycle_id,
                    "ocr": ocr["data"],
                    "order": order,
                    "order_id": order_id,
                    "image_url": image_url,
                    "ocr_provider_result": ocr_provider_result,
                    "high_risk": high_risk,
                },
            )
            steps.append(approval)

        reconciliation = self.reconcile_entries(
            expected_total=expected_total,
            actual_total=actual_total,
            reference=reference,
        )
        steps.append(reconciliation)

        alert_items = []
        if reconciliation["status"] == "mismatch":
            alert_items.append(
                {
                    "id": f"{cycle_id}-difference",
                    "amount": abs(float(reconciliation["data"].get("difference", 0) or 0)),
                    "reference": reference,
                    "reason": "reconciliation_mismatch",
                }
            )
        alerts = self.generate_alerts(items=alert_items, threshold=0)
        steps.append(alerts)

        retry: Optional[Dict[str, Any]] = None
        if retry_error:
            retry = self.record_retry(task_id=f"{cycle_id}-retry", error=retry_error, attempt=retry_attempt)
            steps.append(retry)

        report = self.create_daily_report(date=date)
        steps.append(report)

        status = "needs_review" if approval or reconciliation["status"] == "mismatch" else "completed"
        payload = {
            "project_id": "cloth",
            "cycle_id": cycle_id,
            "status": status,
            "reference": reference,
            "order_id": order_id,
            "image_url": image_url,
            "expected_total_source": "order" if order_total is not None else "payload",
            "actual_total_source": "ocr" if ocr_provider_result else "payload",
            "review_reasons": review_reasons,
            "steps": steps,
            "order": order,
            "ocr_provider_result": ocr_provider_result,
            "ocr": ocr,
            "reconciliation": reconciliation,
            "alerts": alerts,
            "approval": approval,
            "retry": retry,
            "daily_report": report,
        }
        self.memory.save_memory(["buyeros", "close_cycles"], cycle_id, payload, created_by="business_automation")
        return AutomationResult(True, "close_cycle", status, "CLOTH 收單流程已完成並寫入共同記憶。", payload).to_dict()

    def _extract_amount(self, text: str) -> Optional[float]:
        import re

        match = re.search(r"(?:HKD|港幣|\$)\s*([0-9]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if not match:
            return None
        return float(match.group(1))

    def _get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        if not self.orders_service:
            return {"order_id": order_id, "error": "orders_service_not_configured"}
        try:
            return self.orders_service.get_order(order_id)
        except Exception as exc:
            return {"order_id": order_id, "error": str(exc)}

    def _extract_order_total(self, order: Dict[str, Any]) -> Optional[float]:
        for key in ("total_hkd", "total", "amount", "total_price"):
            value = order.get(key)
            amount = self._coerce_amount(value)
            if amount is not None:
                return amount
        return None

    def _coerce_amount(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        import re

        match = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", text)
        return float(match.group(1)) if match else None
