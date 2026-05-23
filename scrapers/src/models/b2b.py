"""Pydantic models for B2B contact finder scraper."""

from typing import Any

from pydantic import Field

from src.models.base import BaseScrapedItem


class B2BContact(BaseScrapedItem):
    """
    B2B contact record from Apollo.io / Hunter.io.
    """

    first_name: str = Field(default="")
    last_name: str = Field(default="")
    full_name: str = Field(default="")
    title: str = Field(default="")
    company: str = Field(default="")
    industry: str = Field(default="")
    seniority_level: str = Field(default="")
    department: str = Field(default="")
    linkedin_url: str = Field(default="")
    email: str = Field(default="")
    phone: str = Field(default="")
    city: str = Field(default="")
    country: str = Field(default="")
    source: str = Field(default="", description="Data source: 'apollo' or 'hunter'")
    raw_data: dict[str, Any] = Field(default_factory=dict)


class UKCompany(BaseScrapedItem):
    """
    UK company record from Companies House.
    """

    number: str = Field(default="", description="Company registration number")
    title: str = Field(default="", description="Company name")
    company_type: str = Field(default="")
    status: str = Field(default="")
    jurisdiction: str = Field(default="")
    address_line_1: str = Field(default="")
    locality: str = Field(default="")
    postal_code: str = Field(default="")
    country: str = Field(default="")
    incorporation_date: str = Field(default="")
    nature_of_business: str = Field(default="")
    accounts_next_due: str = Field(default="")
    sic_codes: str = Field(default="")
    detail_url: str = Field(default="")
