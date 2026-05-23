"""
FastAPI REST API server for the scrapers package.

Run with:
    uvicorn src.api.server:app --reload --port 8000

Docs at: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.jobs import job_queue
from src.metrics import queued_jobs
from src.metrics_app import metrics_app

_LOG = logging.getLogger(__name__)


# ── Request / response models ────────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    """Request body for the /scrape endpoint."""

    scraper: str = Field(..., description="Scraper name: amazon, ebay, supermarket")
    params: dict[str, Any] = Field(default_factory=dict)
    use_cache: bool = Field(default=True, description="Enable Redis cache for this job")
    use_browser: bool = Field(default=False, description="Use Playwright headless browser")


class JobResponse(BaseModel):
    """Response body for /scrape and job lookup."""

    job_id: str
    status: str
    created_at: str


class JobDetailResponse(BaseModel):
    """Full job detail including result or error."""

    id: str
    scraper: str
    status: str
    created_at: str
    result: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    queue_size: int
    job_count: int


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop observability on app startup/shutdown."""
    from src import observability  # noqa: F401

    _LOG.info("Scrapers API started")
    yield
    job_queue.shutdown()
    _LOG.info("Scrapers API stopped")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Scrapers API",
    version="1.0.0",
    description="REST API for the multi-platform scraping CLI",
    lifespan=lifespan,
)

# Mount Prometheus metrics at /metrics
app.mount("/metrics", metrics_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────────


@app.post("/scrape", response_model=JobResponse, tags=["scraping"])
def enqueue_scrape(req: ScrapeRequest, background: BackgroundTasks) -> JobResponse:
    """
    Enqueue a scrape job to run in the background.

    The job runs asynchronously. Poll ``GET /scrape/{job_id}`` for status.
    """
    queued_jobs.inc()
    job = job_queue.enqueue(
        scraper=req.scraper,
        params=req.params,
        use_cache=req.use_cache,
        use_browser=req.use_browser,
    )
    _LOG.info("[api] Enqueued %s job %s", req.scraper, job["id"])
    return JobResponse(
        job_id=job["id"],
        status=job["status"],
        created_at=job["created_at"],
    )


@app.get("/scrape/{job_id}", response_model=JobDetailResponse, tags=["scraping"])
def get_job(job_id: str) -> JobDetailResponse:
    """Retrieve a job by its ID. Returns 404 if not found."""
    job = job_queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return JobDetailResponse(
        id=job["id"],
        scraper=job["scraper"],
        status=job["status"],
        created_at=job["created_at"],
        result=job.get("result", []),
        error=job.get("error"),
    )


@app.get("/jobs", response_model=list[JobResponse], tags=["scraping"])
def list_jobs() -> list[JobResponse]:
    """List the most recent 50 jobs."""
    jobs = job_queue.list_all(limit=50)
    return [
        JobResponse(job_id=j["id"], status=j["status"], created_at=j["created_at"]) for j in jobs
    ]


@app.delete("/scrape/{job_id}", status_code=204, tags=["scraping"])
def delete_job(job_id: str) -> None:
    """Delete a job from the queue. Does nothing if the job is not found."""
    with job_queue._lock:  # noqa: SLF001  — internal access needed for queue management
        if job_id in job_queue._jobs:
            del job_queue._jobs[job_id]
    _LOG.info("[api] Deleted job %s", job_id)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Basic health check."""
    return HealthResponse(
        status="ok",
        queue_size=job_queue.queue_size,
        job_count=job_queue.job_count,
    )
