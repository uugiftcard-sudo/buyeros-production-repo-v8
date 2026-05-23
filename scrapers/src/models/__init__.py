"""Data models for all scrapers."""

from src.models.aliexpress import AliExpressProduct
from src.models.base import BaseScrapedItem

__all__ = ["AliExpressProduct", "BaseScrapedItem"]
