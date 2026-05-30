"""State models used by the BuyerOS supervisor workflow."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


class BuyerOSState(TypedDict, total=False):
    """Runtime state passed between workflow nodes."""

    message: str
    user_id: str
    channel: str
    intent: str
    transaction_id: Optional[str]
    agent: str
    provider: Optional[str]
    session_id: Optional[str]
    task_id: Optional[str]
    memory_hits: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    reply: str


class ContextWriteRequest(BaseModel):
    source_provider: str
    content: Dict[str, Any]
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    memory_key: Optional[str] = None
    summary: Optional[str] = None
    created_by: Optional[str] = None


class ContextSearchRequest(BaseModel):
    query: Optional[str] = None
    source_provider: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=50)


class ContextSummarizeRequest(BaseModel):
    query: Optional[str] = None
    source_provider: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)


class AgentRunRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    user_id: str = "api"
    channel: str = "api"
    session_id: Optional[str] = None
    task_id: Optional[str] = None


class DailyReportRequest(BaseModel):
    date: Optional[str] = None


class OcrPostingRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = "api"
    entry_id: Optional[str] = None


class ReconcileRequest(BaseModel):
    expected_total: float
    actual_total: float
    reference: str = "api"


class AlertItem(BaseModel):
    id: Optional[str] = None
    amount: float = 0

    model_config = {"extra": "allow"}


class AlertsRequest(BaseModel):
    items: List[AlertItem] = Field(default_factory=list)
    threshold: float = 0


class ApprovalRequest(BaseModel):
    task_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class RetryRequest(BaseModel):
    task_id: str = Field(min_length=1)
    error: str = Field(min_length=1)
    attempt: int = Field(default=1, ge=1)


class CloseCycleRequest(BaseModel):
    ocr_text: str = Field(default="UI 測試 OCR 入帳 HKD 88", min_length=1)
    expected_total: Optional[float] = None
    actual_total: Optional[float] = None
    order_id: Optional[str] = None
    image_url: Optional[str] = None
    ocr_language: str = "eng"
    reference: str = "ui-close-cycle"
    source: str = "api"
    retry_error: Optional[str] = None
    retry_attempt: int = Field(default=1, ge=1)
    high_risk: bool = False
    date: Optional[str] = None


class ReceiptScanRequest(BaseModel):
    image_url: str = Field(min_length=8)
    buyer_id: str = Field(min_length=2)
    team_id: Optional[str] = None
    declaration_id: Optional[str] = None
    scan_id: Optional[str] = None
    date: Optional[str] = None
    reference: str = "recon-receipt-scan"
    source: str = "api"
    language: str = "zh"


class ReconCompareRequest(BaseModel):
    declaration_id: str = Field(min_length=2)
    scan_id: str = Field(min_length=2)
    buyer_id: str = Field(min_length=2)
    team_id: Optional[str] = None
    date: Optional[str] = None
    threshold: float = Field(default=0.72, ge=0.5, le=0.95)
    reference: str = "recon-compare"
    source: str = "api"


class RefundCardVerifyRequest(BaseModel):
    return_id: str = Field(min_length=2)
    refund_card_last4: str = Field(min_length=4, max_length=4)
    buyer_id: Optional[str] = None
    team_id: Optional[str] = None
    reference: str = "refund-card-verify"
    source: str = "api"


class BankImportCsvRequest(BaseModel):
    bank_code: str = Field(min_length=2)
    account_id: str = Field(min_length=2)
    currency: str = Field(default="HKD")
    team_id: Optional[str] = None
    buyer_id: Optional[str] = None
    statement_id: Optional[str] = None
    reference: str = "bank-import-csv"
    source: str = "api"


class ReportCreateRequest(BaseModel):
    period: str = "daily"
    date: Optional[str] = None


class ReportExportRequest(BaseModel):
    report_id: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class PromoCampaignRequest(BaseModel):
    name: str = Field(min_length=1)
    offer: str = Field(min_length=1)
    channel: str = "manual"
    budget_hkd: float = Field(default=0, ge=0)
    utm_source: str = "buyeros"
    utm_campaign: Optional[str] = None


class PromoEventRequest(BaseModel):
    campaign_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    value_hkd: float = 0
    source: str = "ui"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    lane: str = "buyeros"
    owner_provider: str = "openai"
    priority: str = "P1"
    payload: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusRequest(BaseModel):
    status: str = Field(min_length=1)
    note: Optional[str] = None


class TaskRunRequest(BaseModel):
    result: str = Field(min_length=1)
    provider: str = "openai"


class ProjectUpsertRequest(BaseModel):
    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: str = "external"
    source: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class MemoryTimelineRequest(BaseModel):
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    query: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)


class TaskDispatchRequest(BaseModel):
    project: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None


class DispatchPlanRequest(BaseModel):
    project: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None
    max_steps: int = Field(default=5, ge=1, le=12)


class SubtaskRunRequest(BaseModel):
    subtask_id: str = Field(min_length=1)
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None


class TaskRunAllRequest(BaseModel):
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None
    max_steps: int = Field(default=50, ge=1, le=200)
