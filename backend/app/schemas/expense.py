"""Pydantic schemas for expense validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ExpenseCreate(BaseModel):
    """Schema for creating an expense."""
    
    buyer_name: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0, le=1_000_000)
    description: str = Field(min_length=1, max_length=1000)
    category: str = Field(default="other", max_length=50)
    receipt_url: str | None = Field(default=None, max_length=500)
    
    @field_validator("buyer_name", "description", "category")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"travel", "office", "marketing", "software", "hardware", "other"}
        if v.lower() not in allowed:
            return "other"
        return v.lower()


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""
    
    status: str | None = Field(default=None)
    reviewer_note: str | None = Field(default=None, max_length=500)
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"approved", "rejected", "pending"}
        if v.lower() not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v.lower()
