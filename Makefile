# Article Summarizer Agent — Developer shortcuts
# Usage: make <target>

PYTHON   ?= python
VENV     := .venv
PIP      := $(VENV)/bin/pip
PYTEST   := $(VENV)/bin/pytest
RUFF     := $(VENV)/bin/ruff
GUNICORN := $(VENV)/bin/gunicorn

IMAGE_NAME ?= article-summarizer
IMAGE_TAG  ?= latest

.PHONY: help setup install lint format test test-db run run-dev docker-build docker-run clean worker flower migrate db-upgrade db-downgrade load-test

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Environment ──────────────────────────────────────────────────────────────

setup:         ## Create virtualenv and install all dependencies
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install ruff pytest pytest-cov
	@echo "\n✓ Environment ready. Activate with: source $(VENV)/bin/activate"

install:       ## Install / sync dependencies (venv must exist)
	$(PIP) install -r requirements.txt

# ── Code quality ─────────────────────────────────────────────────────────────

lint:          ## Lint with ruff
	$(RUFF) check .

format:        ## Auto-format with ruff
	$(RUFF) format .

lint-fix:      ## Lint and auto-fix safe issues
	$(RUFF) check --fix .

# ── Tests ─────────────────────────────────────────────────────────────────────

test:          ## Run test suite (excludes DB integration tests)
	$(PYTEST) tests/ -v --ignore=tests/test_db_integration.py

test-db:       ## Run DB integration tests (requires PostgreSQL)
	$(PYTEST) tests/test_db_integration.py -v

test-cov:      ## Run tests with coverage report
	$(PYTEST) tests/ --cov --cov-report=term-missing --ignore=tests/test_db_integration.py

# ── Run ──────────────────────────────────────────────────────────────────────

run:           ## Run the web app (Flask dev server)
	FLASK_DEBUG=true $(PYTHON) app.py

run-prod:      ## Run with Gunicorn (production-like)
	$(GUNICORN) --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 app:app

run-cli:       ## Run CLI (set URL= to override)
	$(PYTHON) main.py --url "$(URL)"

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:  ## Build Docker image
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run:    ## Run Docker container (requires .env)
	docker run --rm -p 5000:5000 --env-file .env $(IMAGE_NAME):$(IMAGE_TAG)

docker-compose-up:  ## Start with Docker Compose
	docker compose up --build

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:         ## Remove build artefacts and cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .cache outputs/*.txt outputs/*.md outputs/*.json 2>/dev/null || true
	@echo "✓ Cleaned."

worker:        ## Start Celery worker
	$(VENV)/bin/celery -A celery_app worker --loglevel=info

flower:        ## Start Flower Celery monitoring dashboard (requires Redis)
	$(VENV)/bin/celery -A celery_app flower --port=5555

migrate:       ## Create a new Alembic migration
	$(VENV)/bin/alembic revision --autogenerate -m "$(MSG)"

db-upgrade:    ## Apply pending Alembic migrations
	$(VENV)/bin/alembic upgrade head

db-downgrade:  ## Rollback last migration
	$(VENV)/bin/alembic downgrade -1

load-test:     ## Run Locust load tests (requires locust installed)
	$(VENV)/bin/locust -f tests/load/locustfile.py --host=http://localhost:5000
