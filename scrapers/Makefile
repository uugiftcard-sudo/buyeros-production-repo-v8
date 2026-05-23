.PHONY: help install install-dev install-pro install-full test lint lint-fix clean scrape docker-build docker-run docker-up docker-clean api dashboard setup-hooks

# ──────────────────────────────────────────────────────────────
# Project: scrapers
# A professional multi-platform scraping CLI toolkit.
# ──────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  scrapers — Professional Multi-Platform Scraping CLI"
	@echo ""
	@echo "  Available targets:"
	@echo "    install        Install package + dependencies (editable)"
	@echo "    test           Run tests with pytest"
	@echo "    lint           Run ruff linter"
	@echo "    lint-fix       Auto-fix lint issues"
	@echo "    clean          Remove build artifacts"
	@echo "    scrape         Run a scraper (pass ARGS)"
	@echo ""
	@echo "  Docker targets:"
	@echo "    docker-build   Build Docker image"
	@echo "    docker-run     Run a scraper in Docker (pass SCRAPER_ARGS)"
	@echo "    docker-up      Run quick examples (amazon / supermarket / ebay)"
	@echo ""
	@echo "  Usage examples:"
	@echo "    make install"
	@echo "    make test"
	@echo "    make scrape ARGS='amazon --keyword laptop'"
	@echo "    make docker-build"
	@echo "    make docker-run SCRAPER_ARGS='amazon --keyword laptop --pages 2'"
	@echo "    make docker-up EXAMPLE=amazon"
	@echo ""

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/

lint-fix:
	ruff check src/ --fix

clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache

scrape:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make scrape ARGS='<scraper> <args>'"; \
		echo "Example: make scrape ARGS='amazon --keyword laptop'"; \
	else \
		scrapers $(ARGS); \
	fi

# ── Docker ─────────────────────────────────────────────────────

docker-build:
	docker build -t scrapers .

docker-run:
	@if [ -z "$(SCRAPER_ARGS)" ]; then \
		echo "Usage: make docker-run SCRAPER_ARGS='amazon --keyword laptop'"; \
		echo ""; \
		echo "Example commands:"; \
		echo "  make docker-run SCRAPER_ARGS='amazon --keyword laptop --pages 2'"; \
		echo "  make docker-run SCRAPER_ARGS='supermarket -c -k \"whole milk\"'"; \
		echo "  make docker-run SCRAPER_ARGS='ebay --search iphone'"; \
		echo "  make docker-run SCRAPER_ARGS='b2b --domain acme.com'"; \
		echo "  make docker-run SCRAPER_ARGS='trip --type flight --from LHR --to NRT --date 2026-06-15'"; \
	else \
		docker run --rm -it \
			-v "$$(pwd)/output:/app/output" \
			--env-file .env \
			scrapers $(SCRAPER_ARGS); \
	fi

docker-up:
	@docker compose up --rm $(EXAMPLE)

docker-clean:
	docker compose down -v --remove-orphans
	docker rmi scrapers:latest || true

# ── Pro targets ────────────────────────────────────────────────

install-dev:
	pip install -e ".[dev]"

install-pro:
	pip install -e ".[pro]"

install-full:
	pip install -e ".[full]"

setup-hooks:
	pre-commit install

api:
	uvicorn src.api.server:app --reload --port 8000

dashboard:
	python -c "from src.dashboard import run_dashboard; run_dashboard()"

.DEFAULT_GOAL := help
