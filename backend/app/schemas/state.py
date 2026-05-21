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

