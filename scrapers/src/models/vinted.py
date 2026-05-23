"""Pydantic models for Vinted scraper."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from src.models.base import BaseScrapedItem


class ItemCondition(StrEnum):
    """Vinted item condition grades."""

    NEW_WITH_TAGS = "new_with_tags"
    NEW_WITHOUT_TAGS = "new_without_tags"
    VERY_GOOD = "very_good"
    GOOD = "good"
    SATISFACTORY = "satisfactory"


class ItemStatus(StrEnum):
    """Vinted listing status."""

    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"


class Gender(StrEnum):
    """Gender classification."""

    MALE = "male"
    FEMALE = "female"
    UNISEX = "unisex"


class SellerResult(BaseScrapedItem):
    """
    Vinted seller / user profile data.
    """

    seller_id: str = Field(default="")
    username: str = Field(default="")
    real_name: str = Field(default="")
    profile_url: str = Field(default="")
    photo_url: str = Field(default="")
    rating: float = Field(default=0.0)
    review_count: int = Field(default=0)
    member_since: str = Field(default="")
    location: str = Field(default="")
    country_code: str = Field(default="")
    is_verified: bool = Field(default=False)
    item_count: int = Field(default=0)
    follower_count: int = Field(default=0)
    bio: str = Field(default="")


class VintedProduct(BaseScrapedItem):
    """
    Vinted fashion item listing.

    Covers clothing, shoes, bags, and accessories across UK/European marketplace.
    """

    # ── Identity ──────────────────────────────────────────────────
    item_id: str = Field(default="", description="Vinted internal item ID")
    url: str = Field(default="", description="Public listing URL")

    # ── Product info ─────────────────────────────────────────────
    title: str = Field(default="")
    description: str = Field(default="")
    brand_id: int = Field(default=0, description="Vinted brand numeric ID")
    brand_name: str = Field(default="")
    category: str = Field(default="")
    subcategory: str = Field(default="")
    color: str = Field(default="")
    material: str = Field(default="")
    gender: Gender | None = Field(default=None)
    size: str = Field(default="")

    # ── Condition ────────────────────────────────────────────────
    condition: ItemCondition | None = Field(default=None)

    # ── Pricing ─────────────────────────────────────────────────
    price: float = Field(default=0.0, description="Current price in GBP")
    currency: str = Field(default="GBP")
    original_price: float = Field(
        default=0.0, description="Original retail price (filled when discounted)"
    )
    is_discounted: bool = Field(default=False, description="True when price < original_price")

    # ── Status ──────────────────────────────────────────────────
    status: ItemStatus = Field(default=ItemStatus.ACTIVE)

    # ── Media ───────────────────────────────────────────────────
    photos: list[str] = Field(
        default_factory=list, description="Full-resolution photo URLs"
    )

    # ── Seller ─────────────────────────────────────────────────
    seller_id: str = Field(default="")
    seller_username: str = Field(default="")
    seller_rating: float = Field(default=0.0)
    seller_reviews: int = Field(default=0)

    # ── Engagement ───────────────────────────────────────────────
    views: int = Field(default=0)
    watchers: int = Field(default=0)
    posted_at: str = Field(default="")
    updated_at: str = Field(default="")

    # ── Search context ───────────────────────────────────────────
    search_keyword: str = Field(default="")

    def to_csv_dict(self) -> dict[str, Any]:
        """Flatten lists/dicts and convert enums to strings for CSV output."""
        result: dict[str, Any] = {}
        for name in type(self).model_fields:
            value = getattr(self, name)
            if value is None:
                result[name] = ""
            elif isinstance(value, Enum):
                result[name] = value.value
            elif isinstance(value, list):
                import json

                result[name] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, dict):
                import json

                result[name] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, datetime):
                result[name] = value.isoformat()
            else:
                result[name] = value
        return result
