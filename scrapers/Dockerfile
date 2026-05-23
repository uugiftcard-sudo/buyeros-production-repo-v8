# ──────────────────────────────────────────────────────────────
# Dockerfile — scrapers
# Multi-stage build for a small, secure production image.
#
# Usage:
#   docker build -t scrapers .
#   docker run --rm -it scrapers --help
#   docker run --rm -it \
#     -v $(pwd)/output:/app/output \
#     -e APOLLO_API_KEY=xxx \
#     -e HUNTER_API_KEY=yyy \
#     scrapers amazon --keyword laptop
# ──────────────────────────────────────────────────────────────

# ── Stage 1: Builder ────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1000 scrapers && \
    useradd --uid 1000 --gid scrapers --shell /bin/bash scrapers

WORKDIR /app

# Install runtime deps (browser libs for lxml)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1 \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project (skip tests, docs, cache)
COPY --chown=scrapers:scrapers pyproject.toml config.yaml ./
COPY --chown=scrapers:scrapers src/ ./src/
COPY --chown=scrapers:scrapers .env.example ./

# Output directory
RUN mkdir -p /app/output && chown scrapers:scrapers /app/output
WORKDIR /app/output

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OUTPUT_DIR=/app/output

# Switch to non-root user
USER scrapers

ENTRYPOINT ["scrapers"]
CMD ["--help"]
