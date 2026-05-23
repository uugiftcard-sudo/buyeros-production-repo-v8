"""Pydantic models for Trip.com scraper."""

from pydantic import Field

from src.models.base import BaseScrapedItem


class FlightResult(BaseScrapedItem):
    """
    Flight search result from Trip.com.
    """

    airline: str = Field(default="")
    flight_no: str = Field(default="")
    depart_time: str = Field(default="")
    arrive_time: str = Field(default="")
    depart_airport: str = Field(default="")
    arrive_airport: str = Field(default="")
    duration: str = Field(default="")
    price: str = Field(default="")
    currency: str = Field(default="CNY")
    cabin_class: str = Field(default="economy")
    stops: str = Field(default="", description="Number of stops")
    aircraft_type: str = Field(default="")
    search_url: str = Field(default="")


class HotelResult(BaseScrapedItem):
    """
    Hotel search result from Trip.com.
    """

    name: str = Field(default="")
    star_rating: str = Field(default="", description="Star rating")
    user_rating: str = Field(default="", description="User review score")
    review_count: str = Field(default="")
    location: str = Field(default="", description="Landmark / district")
    district: str = Field(default="")
    price: str = Field(default="")
    currency: str = Field(default="CNY")
    original_price: str = Field(default="")
    discount: str = Field(default="")
    amenities: str = Field(default="", description="Comma-separated facility list")
    has_breakfast: str = Field(default="No")
    free_cancellation: str = Field(default="No")
    image_url: str = Field(default="")
    detail_url: str = Field(default="")


class AttractionResult(BaseScrapedItem):
    """
    Attraction / point-of-interest result from Trip.com.
    """

    name: str = Field(default="")
    category: str = Field(default="")
    location: str = Field(default="")
    city: str = Field(default="")
    rating: str = Field(default="")
    review_count: str = Field(default="")
    ticket_price: str = Field(default="")
    currency: str = Field(default="CNY")
    description: str = Field(default="")
    opening_hours: str = Field(default="")
    image_url: str = Field(default="")
    detail_url: str = Field(default="")
