"""Pydantic request/state models used by BuyerOS runtime routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field
from pydantic import field_validator


class BuyerOSState(TypedDict, total=False):
    message: str
    user_id: str
    channel: str
    provider: Optional[str]
    session_id: Optional[str]
    task_id: Optional[str]
    transaction_id: Optional[str]
    intent: str
    agent: str
    memory_hits: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    reply: str


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ContextWriteRequest(FlexibleModel):
    source_provider: str = "api"
    content: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    memory_key: Optional[str] = None
    summary: Optional[str] = None
    created_by: Optional[str] = None


class ContextSearchRequest(FlexibleModel):
    query: Optional[str] = None
    source_provider: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = 5


class ContextSummarizeRequest(ContextSearchRequest):
    pass


class ReceiptScanRequest(FlexibleModel):
    image_url: str
    scan_id: Optional[str] = None
    buyer_id: Optional[str] = None
    team_id: Optional[str] = None
    declaration_id: Optional[str] = None
    date: Optional[str] = None


class ReconCompareRequest(FlexibleModel):
    declaration_id: str
    scan_id: str
    threshold: float = 0.01
    buyer_id: Optional[str] = None
    team_id: Optional[str] = None
    date: Optional[str] = None


class RefundCardVerifyRequest(FlexibleModel):
    return_id: str
    refund_card_last4: str
    buyer_id: Optional[str] = None


class BankImportCsvRequest(FlexibleModel):
    bank_code: str
    account_id: str
    currency: str = "HKD"
    team_id: Optional[str] = None
    buyer_id: Optional[str] = None
    statement_id: Optional[str] = None
    source: str = "api"
    reference: str = "bank-import"
    raw_text: Optional[str] = None


class AgentRunRequest(FlexibleModel):
    user_id: str = "api"
    prompt: str
    channel: str = "api"
    provider: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None


class ProjectUpsertRequest(FlexibleModel):
    project_id: str


class MemoryTimelineRequest(FlexibleModel):
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    query: Optional[str] = None
    limit: int = 50


class DailyReportRequest(FlexibleModel):
    date: Optional[str] = None


class OcrPostingRequest(FlexibleModel):
    text: str
    source: str = "api"
    entry_id: Optional[str] = None


class ReconcileRequest(FlexibleModel):
    expected_total: float
    actual_total: float
    reference: str


class AlertsRequest(FlexibleModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    threshold: float = 0


class ApprovalRequest(FlexibleModel):
    task_id: str
    reason: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class RetryRequest(FlexibleModel):
    task_id: str
    error: str
    attempt: int = 1


class CloseCycleRequest(FlexibleModel):
    ocr_text: str = ""
    expected_total: float = 0
    actual_total: float = 0
    order_id: Optional[str] = None
    image_url: Optional[str] = None
    ocr_language: str = "eng"
    reference: str = "close-cycle"
    source: str = "api"
    retry_error: Optional[str] = None
    retry_attempt: int = 0
    high_risk: bool = False
    date: Optional[str] = None


class ReportCreateRequest(FlexibleModel):
    period: str = "daily"
    date: Optional[str] = None


class ReportExportRequest(FlexibleModel):
    report_id: Optional[str] = None
    limit: int = 100


class PromoCampaignRequest(FlexibleModel):
    name: str
    offer: str
    channel: str = "web"
    budget_hkd: float = 0
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None

    @field_validator("name", "offer")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field is required")
        return value


class PromoEventRequest(FlexibleModel):
    campaign_id: str
    event_type: str
    value_hkd: float = 0
    source: str = "api"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskCreateRequest(FlexibleModel):
    title: str
    lane: str = "buyer_ai"
    owner_provider: str = "openai"
    priority: str = "P2"
    payload: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusRequest(FlexibleModel):
    status: str
    note: Optional[str] = None


class TaskRunRequest(FlexibleModel):
    result: str
    provider: str = "api"


class TaskDispatchRequest(FlexibleModel):
    project: str = "buyer_ai"
    task_type: str = "planning"
    title: str
    prompt: str
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None


class DispatchPlanRequest(TaskDispatchRequest):
    max_steps: int = 3


class SubtaskRunRequest(FlexibleModel):
    subtask_id: Optional[str] = None
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None


class TaskRunAllRequest(FlexibleModel):
    preferred_provider: Optional[str] = None
    session_id: Optional[str] = None
    max_steps: int = 10
