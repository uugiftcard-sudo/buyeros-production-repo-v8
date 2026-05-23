"""Base Pydantic models for all scrapers."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseScrapedItem(BaseModel):
    """
    Root model that all scraper models extend.

    Provides common fields (scraped_at) and utility methods
    for serialization and CSV-safe field access.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_default=True,
    )

    scraped_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="ISO-8601 timestamp of when this item was scraped",
    )

    def to_csv_dict(self) -> dict[str, Any]:
        """
        Return a flat dict suitable for CSV writing.

        - Converts all None values to empty strings
        - Converts lists/dicts to JSON strings
        """
        result: dict[str, Any] = {}
        for name in type(self).model_fields:
            value = getattr(self, name)
            if value is None:
                result[name] = ""
            elif isinstance(value, list):
                import json

                result[name] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, dict):
                import json

                result[name] = json.dumps(value, ensure_ascii=False)
            else:
                result[name] = value
        return result

    def model_post_init(self, _: Any) -> None:
        pass


class HTTPError(BaseModel):
    """Record of a failed HTTP request — stored for audit/debugging."""

    url: str
    status_code: int | None = None
    error_message: str = ""
    attempt: int = 1


class ScrapeResult(BaseModel, Generic[T]):
    """
    Container for scrape operation results.

    Type-annotate with the model, e.g.:
        result: ScrapeResult[LinkedInProfile]
    """

    items: list[T] = Field(default_factory=list)
    errors: list[HTTPError] = Field(default_factory=list)
    total_requests: int = 0
    successful_requests: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.successful_requests / self.total_requests, 3)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0
