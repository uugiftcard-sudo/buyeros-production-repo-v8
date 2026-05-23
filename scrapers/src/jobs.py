"""
Background job queue — thread-safe, in-process, FIFO.

Queues are stored in memory and lost on restart. For persistence, swap
to Redis-backed queues (rq, Celery) or a database.

Usage:
    from src.jobs import job_queue

    job = job_queue.enqueue("amazon", {"keyword": "laptop", "pages": 2})
    print(job["id"])  # "a1b2c3d4"

    result = job_queue.get(job["id"])
    print(result["status"])  # "done"
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.models.base import BaseScrapedItem

__all__ = ["Job", "JobQueue", "job_queue"]


@dataclass
class Job:
    """Represents a single queued scrape job."""

    id: str
    scraper: str
    params: dict[str, Any]
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    result: list[BaseScrapedItem] | None = None
    error: str | None = None
    use_cache: bool = True
    use_browser: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scraper": self.scraper,
            "params": self.params,
            "status": self.status,
            "created_at": str(self.created_at),
            "result": [i.model_dump() for i in (self.result or [])],
            "error": self.error,
            "use_cache": self.use_cache,
            "use_browser": self.use_browser,
        }


class JobQueue:
    """
    Thread-safe FIFO job queue with in-memory storage.

    The worker loop runs in a daemon thread and dispatches jobs to the
    appropriate scraper function.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._jobs: dict[str, Job] = {}
        self._q: queue.Queue[tuple] = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    # ── Enqueue / query ─────────────────────────────────────────────────────

    def enqueue(
        self,
        scraper: str,
        params: dict[str, Any],
        use_cache: bool = True,
        use_browser: bool = False,
    ) -> dict[str, Any]:
        """Add a job to the queue and return its metadata."""
        job = Job(
            id=str(uuid.uuid4())[:8],
            scraper=scraper,
            params=params,
            use_cache=use_cache,
            use_browser=use_browser,
        )
        with self._lock:
            self._jobs[job.id] = job

        self._q.put_nowait((job.id, params, use_cache, use_browser))
        return {
            "id": job.id,
            "status": job.status,
            "created_at": str(job.created_at),
        }

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Return job metadata + result. None if job_id not found."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return None
        return job.to_dict()

    def list_all(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent `limit` jobs."""
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    @property
    def queue_size(self) -> int:
        return self._q.qsize()

    @property
    def job_count(self) -> int:
        with self._lock:
            return len(self._jobs)

    # ── Internal worker ────────────────────────────────────────────────────

    def _worker(self) -> None:
        """Daemon thread: pop jobs from the queue and dispatch them."""
        while self._running:
            try:
                job_id, params, use_cache, use_browser = self._q.get(timeout=1.0)
            except queue.Empty:
                continue

            with self._lock:
                job = self._jobs.get(job_id)
            if job is None:
                continue

            job.status = "running"

            try:
                result_items = self._dispatch(job.scraper, params, use_cache, use_browser)
                job.result = result_items
                job.status = "done"
            except Exception as exc:  # noqa: BLE001
                job.error = str(exc)
                job.status = "failed"

            self._q.task_done()

    def _dispatch(
        self,
        scraper: str,
        params: dict[str, Any],
        use_cache: bool,
        use_browser: bool,
    ) -> list[BaseScrapedItem]:
        """
        Dispatch to the correct scraper and return typed results.

        This is the plug-in point — add new scrapers here as they are added.
        """
        # Import lazily so the core CLI does not need FastAPI/pro deps at import time
        from src.scrapers.amazon import AmazonScraper
        from src.scrapers.ebay import EbayScraper
        from src.scrapers.supermarket import SupermarketScraper

        keyword = params.get("keyword", "")
        pages = params.get("pages", 1)
        retailer = params.get("retailer", "all")

        if scraper == "amazon":
            svc = AmazonScraper(domain=params.get("domain", "com"))
            items = svc.search_by_keyword(keyword, pages=pages)
            return items

        if scraper == "supermarket":
            svc = SupermarketScraper()
            items = svc.search(retailer=retailer, keyword=keyword)
            return items

        if scraper == "ebay":
            svc = EbayScraper()
            items = svc.search_by_keyword(keyword)
            return items

        raise ValueError(f"Unknown scraper: {scraper!r}")

    def shutdown(self) -> None:
        """Stop the worker thread cleanly. Call on app shutdown."""
        self._running = False
        self._worker_thread.join(timeout=5.0)


# ── Module-level singleton ──────────────────────────────────────────────────────

job_queue = JobQueue()
