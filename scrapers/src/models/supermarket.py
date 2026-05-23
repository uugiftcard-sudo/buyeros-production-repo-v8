"""Pydantic models for UK supermarket scraper."""

from pydantic import Field

from src.models.base import BaseScrapedItem


class SupermarketResult(BaseScrapedItem):
    """
    Supermarket product listing.
    Covers John Lewis, Tesco, and M&S.
    """

    name: str = Field(default="")
    brand: str = Field(default="")
    price: str = Field(default="")
    original_price: str = Field(default="")
    currency: str = Field(default="GBP")
    unit_price: str = Field(default="", description="Per-unit price, e.g. £/kg")
    category: str = Field(default="")
    subcategory: str = Field(default="")
    promotion: str = Field(default="", description="Promo label, e.g. 'Save £2'")
    rating: str = Field(default="")
    review_count: str = Field(default="")
    availability: str = Field(default="")
    image_url: str = Field(default="")
    product_url: str = Field(default="")
    retailer: str = Field(default="", description="John Lewis / Tesco / M&S")
    search_keyword: str = Field(default="")
