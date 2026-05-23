"""Pydantic models for loyalty card checker scraper."""

from typing import Any

from pydantic import Field

from src.models.base import BaseScrapedItem


class NectarAccount(BaseScrapedItem):
    """
    Nectar card account summary.
    """

    card_number: str = Field(default="")
    points_balance: str = Field(default="")
    points_value: str = Field(default="", description="Cash-equivalent value")
    tier: str = Field(default="")
    last_updated: str = Field(default="")
    recent_transactions: list[dict[str, Any]] = Field(default_factory=list)


class TescoClubcard(BaseScrapedItem):
    """
    Tesco Clubcard account summary.
    """

    card_number: str = Field(default="")
    points_balance: str = Field(default="")
    vouchers_available: str = Field(default="")
    last_updated: str = Field(default="")
    recent_transactions: list[dict[str, Any]] = Field(default_factory=list)


class GiftcardBalance(BaseScrapedItem):
    """
    Generic gift card balance record.
    """

    card_name: str = Field(default="")
    last_four: str = Field(default="")
    balance: str = Field(default="")
    currency: str = Field(default="GBP")
    card_type: str = Field(default="")
    expiry: str = Field(default="")
    last_updated: str = Field(default="")
