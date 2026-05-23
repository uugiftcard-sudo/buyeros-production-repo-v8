"""Pydantic models for LinkedIn scraper."""

from pydantic import Field

from src.models.base import BaseScrapedItem


class LinkedInProfile(BaseScrapedItem):
    """
    LinkedIn public profile data.

    Scraped fields from the public-facing profile page.
    """

    name: str = Field(default="", description="Full name from profile heading")
    headline: str = Field(default="", description="Job title / headline")
    company: str = Field(default="", description="Current employer")
    industry: str = Field(default="", description="Industry")
    location: str = Field(default="", description="Geographic location")
    profile_url: str = Field(default="", description="Profile URL")
    about: str = Field(default="", description="About / summary section")
    connections: str = Field(default="", description="Connection count (when visible)")
    raw_html_preview: str = Field(
        default="",
        description="Raw HTML text preview from main section (first 200 chars)",
    )
