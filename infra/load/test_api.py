"""Load testing script for BuyerOS API."""

from __future__ import annotations

import asyncio
import httpx
import time
from statistics import mean, median


async def test_endpoint(
    client: httpx.AsyncClient,
    url: str,
    method: str = "GET",
    data: dict | None = None,
) -> dict:
    """Test a single endpoint."""
    start = time.time()
    try:
        if method == "GET":
            response = await client.get(url)
        else:
            response = await client.post(url, json=data)
        duration = time.time() - start
        return {
            "status": response.status_code,
            "duration": duration,
            "success": 200 <= response.status_code < 300,
        }
    except Exception as exc:
        duration = time.time() - start
        return {
            "status": 0,
            "duration": duration,
            "success": False,
            "error": str(exc),
        }


async def load_test(
    url: str,
    requests_count: int = 100,
    concurrency: int = 10,
) -> dict:
    """Run load test against an endpoint."""
    print(f"Load testing {url} with {requests_count} requests, concurrency={concurrency}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create tasks in batches
        results = []
        for i in range(0, requests_count, concurrency):
            batch = [
                test_endpoint(client, url)
                for _ in range(min(concurrency, requests_count - i))
            ]
            results.extend(await asyncio.gather(*batch))
        
        # Calculate stats
        durations = [r["duration"] for r in results]
        successes = sum(1 for r in results if r["success"])
        failures = requests_count - successes
        
        return {
            "total": requests_count,
            "successes": successes,
            "failures": failures,
            "avg_duration": mean(durations),
            "median_duration": median(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "requests_per_second": requests_count / sum(durations),
        }


async def main() -> None:
    """Main entry point."""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/health",
        "/api/health",
        "/api/status",
        "/api/expenses",
    ]
    
    for endpoint in endpoints:
        print(f"\n{'=' * 60}")
        print(f"Testing: {endpoint}")
        print("=" * 60)
        
        results = await load_test(f"{base_url}{endpoint}")
        
        print(f"Total requests: {results['total']}")
        print(f"Successes: {results['successes']}")
        print(f"Failures: {results['failures']}")
        print(f"Avg duration: {results['avg_duration']:.3f}s")
        print(f"Median duration: {results['median_duration']:.3f}s")
        print(f"Min/Max: {results['min_duration']:.3f}s / {results['max_duration']:.3f}s")
        print(f"RPS: {results['requests_per_second']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
