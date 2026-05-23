"""
Terminal dashboard — live job queue + metrics display using Rich.

Run standalone:
    python -c "from src.dashboard import run_dashboard; run_dashboard()"

Or start both API and dashboard together:
    make dashboard   # via Makefile
"""

from __future__ import annotations

import sys
import threading
import time

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    raise ImportError("Dashboard requires rich: pip install -e '.[pro]'") from None

__all__ = ["run_dashboard"]


def _start_api_server(port: int = 8000) -> None:
    """Start the FastAPI server in a background thread."""
    import uvicorn

    from src.api.server import app

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def _build_jobs_table(jobs: list[dict]) -> Table:
    """Render the jobs table."""
    table = Table(
        title="[bold cyan]Job Queue[/bold cyan]",
        show_lines=True,
        box=None,
        header_style="bold white",
    )
    table.add_column("ID", style="dim", width=9)
    table.add_column("Scraper", style="cyan", width=16)
    table.add_column("Status", width=10)
    table.add_column("Age", justify="right", width=8)
    table.add_column("Error / Result", style="dim")

    for job in jobs[:15]:
        status = job.get("status", "?")
        status_color = {
            "pending": "yellow",
            "running": "bold blue",
            "done": "bold green",
            "failed": "bold red",
        }.get(status, "white")

        age_s = int(time.time() - float(job.get("created_at", time.time())))
        age_str = f"{age_s}s" if age_s < 60 else f"{age_s // 60}m"

        error = job.get("error") or ""
        result_count = len(job.get("result") or [])
        result_str = f"[green]{result_count} items[/green]" if result_count else ""

        detail = error or result_str

        table.add_row(
            job.get("id", ""),
            job.get("scraper", ""),
            f"[{status_color}]{status}[/{status_color}]",
            age_str,
            detail,
        )

    return table


def _build_metrics_panel() -> Panel:
    """Render the metrics summary panel."""
    lines = [
        "  View full metrics at: [bold]http://localhost:8000/metrics[/bold]",
        "",
        "  Available counters:",
        "    scraper_requests_total",
        "    scraper_duration_seconds",
        "    scraper_active_scrapes",
        "    scraper_cache_hits_total",
        "    scraper_cache_misses_total",
        "    scraper_queued_jobs",
        "    scraper_completed_jobs_total",
    ]
    return Panel(
        "\n".join(lines),
        title="[bold]Prometheus Metrics[/bold]",
        border_style="blue",
        padding=(1, 2),
    )


def _render(jobs: list[dict]) -> Layout:
    """Build the full dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="body"),
    )

    # Header
    layout["header"].update(
        Panel(
            Text("SCRAPERS PRO — Dashboard", style="bold cyan on black"),
            subtitle=Text(
                "  http://localhost:8000/docs  |  Press Ctrl+C to exit",
                style="dim",
            ),
            border_style="cyan",
            padding=(0, 2),
        )
    )

    # Body split: jobs left, metrics right
    layout["body"].split_row(
        Layout(name="jobs", ratio=2),
        Layout(name="metrics"),
    )

    layout["jobs"].update(_build_jobs_table(jobs))
    layout["metrics"].update(_build_metrics_panel())

    return layout


def run_dashboard(port: int = 8000) -> None:
    """
    Start the API server and render the live dashboard.

    Blocks the main thread. Press Ctrl+C to exit.
    """
    console = Console()

    # Start API in background thread
    t = threading.Thread(target=_start_api_server, args=(port,), daemon=True)
    t.start()
    time.sleep(1.5)  # Give the server a moment to start

    console.print(
        Panel(
            f"[green]API server running at http://localhost:{port}[/green]\n"
            "[dim]Swagger docs: http://localhost:{port}/docs[/dim]",
            title="[bold]Scrapers Pro Dashboard[/bold]",
            border_style="cyan",
        )
    )

    # Import job queue lazily to avoid import cycles
    from src.jobs import job_queue

    try:
        with Live(
            _render(job_queue.list_all()),
            refresh_per_second=2,
            console=console,
            transient=False,
        ) as live:
            while True:
                time.sleep(1.5)
                live.update(_render(job_queue.list_all()))
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        job_queue.shutdown()
        sys.exit(0)
