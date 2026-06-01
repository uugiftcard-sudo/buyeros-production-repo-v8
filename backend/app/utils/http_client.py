"""Async HTTP client utility for BuyerOS.

Provides a simple async wrapper around httpx for use in FastAPI endpoints.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, Optional


class AsyncHttpClient:
    """Async HTTP client with timeout and error handling."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def post(self, url: str, headers: Optional[Dict[str, str]] = None, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make async POST request."""
        client = await self._get_client()
        try:
            response = await client.post(url, headers=headers, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"error": "timeout", "url": url}
        except httpx.HTTPStatusError as exc:
            return {"error": f"http_{exc.response.status_code}", "url": url}
        except Exception as exc:
            return {"error": str(exc), "url": url}

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make async GET request."""
        client = await self._get_client()
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"error": "timeout", "url": url}
        except httpx.HTTPStatusError as exc:
            return {"error": f"http_{exc.response.status_code}", "url": url}
        except Exception as exc:
            return {"error": str(exc), "url": url}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Global HTTP client instance
_http_client: Optional[AsyncHttpClient] = None


def get_http_client() -> AsyncHttpClient:
    """Get or create the global HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = AsyncHttpClient()
    return _http_client
