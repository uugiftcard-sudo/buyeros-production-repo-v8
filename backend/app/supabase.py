"""Unified Supabase client for BuyerOS."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx


class SupabaseClient:
    """Unified Supabase client with singleton pattern."""

    _instance: Optional[SupabaseClient] = None

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ) -> None:
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_instance(cls) -> SupabaseClient:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    @property
    def configured(self) -> bool:
        """Check if client is configured."""
        return bool(self.url and self.key)

    def get_headers(self) -> dict[str, str]:
        """Get standard Supabase headers."""
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    async def query(
        self,
        table: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Query a table."""
        if not self.configured:
            return []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/{table}",
                headers=self.get_headers(),
                params=params,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def insert(
        self,
        table: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert a record."""
        if not self.configured:
            return {"error": "not configured"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/{table}",
                headers=self.get_headers(),
                json=data,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        """Update records matching filters."""
        if not self.configured:
            return {"error": "not configured"}
        
        headers = self.get_headers()
        headers["Prefer"] = "return=representation"
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.url}/rest/v1/{table}",
                headers=headers,
                json=data,
                params=filters,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
