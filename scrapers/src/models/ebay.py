"""Pydantic models for eBay scraper."""

from pydantic import Field

from src.models.base import BaseScrapedItem


class SellerResult(BaseScrapedItem):
    """
    eBay seller profile data.
    """

    seller_id: str = Field(default="")
    seller_name: str = Field(default="")
    feedback_score: str = Field(default="")
    feedback_percent: str = Field(default="")
    positive_feedback: str = Field(default="")
    neutral_feedback: str = Field(default="")
    negative_feedback: str = Field(default="")
    member_since: str = Field(default="")
    location: str = Field(default="")
    business: bool = Field(default=False)
    top_rated: bool = Field(default=False)
    registration_id: str = Field(default="")
    detail_url: str = Field(default="")


class ItemResult(BaseScrapedItem):
    """
    eBay item / product listing.
    """

    item_id: str = Field(default="")
    title: str = Field(default="")
    price: str = Field(default="")
    currency: str = Field(default="USD")
    condition: str = Field(default="")
    listing_type: str = Field(default="")
    seller_id: str = Field(default="")
    seller_rating: str = Field(default="")
    sold_count: str = Field(default="")
    watching_count: str = Field(default="")
    bids_count: str = Field(default="")
    location: str = Field(default="")
    returns: str = Field(default="")
    shipping: str = Field(default="")
    category: str = Field(default="")
    category_id: str = Field(default="")
    image_url: str = Field(default="")
    detail_url: str = Field(default="")
    end_time: str = Field(default="")
    search_keyword: str = Field(default="")
