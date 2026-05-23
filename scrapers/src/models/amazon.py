"""Pydantic models for Amazon scraper."""

from pydantic import Field

from src.models.base import BaseScrapedItem


class ProductResult(BaseScrapedItem):
    """
    Amazon product listing / search result.
    """

    asin: str = Field(default="")
    title: str = Field(default="")
    price: str = Field(default="")
    original_price: str = Field(default="")
    currency: str = Field(default="USD")
    rating: str = Field(default="")
    review_count: str = Field(default="")
    best_seller_badge: str = Field(default="No")
    amazon_choice: str = Field(default="No")
    category: str = Field(default="")
    subcategory: str = Field(default="")
    rank: str = Field(default="")
    availability: str = Field(default="")
    brand: str = Field(default="")
    seller: str = Field(default="")
    image_url: str = Field(default="")
    detail_url: str = Field(default="")
    search_keyword: str = Field(default="")
