"""Pydantic models for AliExpress scraper."""

from typing import Any

from pydantic import Field

from src.models.base import BaseScrapedItem


class AliExpressProduct(BaseScrapedItem):
    """
    AliExpress product listing — search result or detail page.
    """

    # Core identity
    product_id: str = Field(default="", description="AliExpress product ID / item ID")
    title: str = Field(default="", description="Product title")
    url: str = Field(default="", description="Product detail page URL")

    # Pricing
    price_current: str = Field(default="", description="Current discounted price")
    price_original: str = Field(default="", description="Original / list price")
    currency: str = Field(default="USD", description="Currency code")
    discount_percent: str = Field(default="", description="Discount percentage, e.g. '-70%'")

    # Ratings & social proof
    rating: str = Field(default="", description="Star rating, e.g. '4.8'")
    review_count: str = Field(default="", description="Number of reviews")
    orders_count: str = Field(default="", description="Historical orders / sold count")
    helpful_reviews: str = Field(default="", description="Helpful vote count")

    # Store
    store_name: str = Field(default="", description="Seller store name")
    store_id: str = Field(default="", description="Seller store ID")
    store_rating: str = Field(default="", description="Store rating score")
    store_followers: str = Field(default="", description="Store follower count")
    store_location: str = Field(default="", description="Seller country/location")

    # Category
    category: str = Field(default="", description="Top-level category")
    subcategory: str = Field(default="", description="Sub-category")

    # Shipping
    shipping_price: str = Field(default="", description="Shipping cost")
    shipping_eta: str = Field(default="", description="Estimated delivery time")
    free_shipping: bool = Field(default=False, description="True when shipping is free")

    # Media
    images: list[str] = Field(default_factory=list, description="List of image URLs")
    main_image: str = Field(default="", description="Primary product image URL")

    # Variants & attributes
    variants: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Product variants (colour/size) as dicts",
    )
    attributes: list[dict[str, str]] = Field(
        default_factory=list,
        description="Product attribute key-value pairs",
    )

    # Availability
    availability: str = Field(default="", description="'In Stock', 'Limited', 'Out of Stock', …")
    in_stock: bool = Field(default=True, description="True when item is available")

    # Context
    search_keyword: str = Field(default="", description="Keyword used to find this product")
