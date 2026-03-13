# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Setup and dependencies:**
```bash
make setup          # create .venv + install deps (first time)
make install        # sync deps into existing venv
```

**Development:**
```bash
make run            # Flask dev server on :5000 (FLASK_DEBUG=true)
make run-prod       # Gunicorn (2 workers, 4 threads)
make run-cli URL="https://example.com/article"  # CLI mode
make worker         # Celery worker (requires Redis)
make flower         # Celery monitoring UI on :5555
```

**Database:**
```bash
make migrate MSG="description"  # create Alembic migration
make db-upgrade                 # apply pending migrations
make db-downgrade               # rollback last migration
```

**Code quality:**
```bash
make lint           # ruff check
make format         # ruff format
make lint-fix       # ruff check --fix
```

**Tests:**
```bash
make test                                        # all tests (excludes DB integration)
make test-cov                                    # with coverage report
make test-db                                     # DB integration tests (requires PostgreSQL)
# Single test file or function (WSL2 venv path):
.venv/Scripts/python.exe -m pytest tests/test_ssrf.py -v
.venv/Scripts/python.exe -m pytest tests/test_api.py::TestApiSumarizar::test_valid_request -v
```

> **WSL2 note:** The venv is a Windows venv mounted in WSL. Use `.venv/Scripts/python.exe` directly, not `python` or `source .venv/bin/activate`.

## Architecture

The app follows Clean Architecture with four layers. The pipeline is:

```
URL → validate → scrape → process text → summarise → save files
```

### Layers

```
domain/          — entities (SummarizationTask, User, AuditLogEntry, SettingsEntry),
                   repository interfaces, domain events
application/     — commands, queries, ports, event bus; handlers split into:
                   task_handlers.py, auth_handlers.py, admin_handlers.py
infrastructure/  — SQLAlchemy repos, pipeline runner, auth services, DI container,
                   runtime_settings.py
presentation/    — Flask app factory, blueprints (api, auth, web), helpers.py
modules/         — cross-cutting utilities: cache, circuit_breaker, rate_limiter,
                   secrets_manager, logging_config, web_scraper, etc.
tasks/           — Celery task definitions (summarization_task.py)
```

### Entry points

- **`app.py`** — WSGI entrypoint; calls `create_app()` from `presentation/app_factory.py`.
- **`presentation/app_factory.py`** — wires Flask, JWT, CORS, Swagger, Prometheus, blueprints, and the DI container via `build_runtime_container()`.
- **`infrastructure/container.py`** — `RuntimeContainer` dataclass holding all handlers and repos; built once via `@lru_cache`. `AsyncTaskDispatcher` prefers Celery when available, falls back to daemon threads.
- **`main.py`** — CLI entry point: `ArticleSummarizerAgent.run(url, method, length)` runs the 5-step pipeline directly.

### Blueprints

| Blueprint | Prefix | Purpose |
|---|---|---|
| `api_bp` | `/api/` | REST API — sumarizar, task status, download, settings, cache, metrics |
| `auth_bp` | `/auth/` | Login / logout / refresh JWT |
| `web_bp` | `/` | Server-rendered HTML pages |

Key API endpoints: `POST /api/sumarizar`, `GET /api/tarefa/<task_id>`, `GET /api/download/<task_id>/<fmt>`, `GET /health`, `GET /metrics`, `GET /apidocs/`.

### Configuration (`config.py`)

Single `Config` singleton (`from config import config`). Sub-configs:

| Attribute | Purpose |
|---|---|
| `config.scraping` | HTTP timeout, retries, blocked CIDRs, user-agents |
| `config.processing` | Min sentence/paragraph lengths |
| `config.summarization` | Method (`extractive`/`generative`), length, fallback |
| `config.gemini` | API key, model ID, token limits |
| `config.output` | Output dir, formats, cache TTL |
| `config.rate_limit` | Per-endpoint rate limiting (submit/auth/polling/admin) |
| `config.auth` | JWT expiry, cookie settings, seed admin credentials |
| `config.logging` | Log level |

Key env vars: `SECRET_KEY` (required in prod), `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `DATABASE_URL` (SQLite default, Postgres in prod), `REDIS_URL` / `CELERY_BROKER_URL` (optional — enables Celery), `CORS_ORIGINS`, `ADMIN_TOKEN`, `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`.

### Database

SQLAlchemy ORM with Alembic migrations. `database.py` exports `session_scope()` context manager and `upgrade_schema()` (called at app startup). Default: `sqlite:///./dev.db`. Migrations live in `alembic/versions/`. Models in `models.py`.

### Async task dispatch

`AsyncTaskDispatcher` in `infrastructure/container.py` checks if Celery is reachable at startup:
- **Celery available**: dispatches via `tasks.summarization_task.summarize_article.delay()`
- **Celery unavailable**: falls back to a daemon thread

`celery_app.py` reads `CELERY_BROKER_URL` / `REDIS_URL` (default: `redis://localhost:6379/1`).

### Key modules

| Module | Class/export | Role |
|---|---|---|
| `modules/web_scraper.py` | `WebScraper` | HTTP scraping; calls `_check_ssrf()` + circuit breaker |
| `modules/circuit_breaker.py` | `circuit_breaker` | Per-hostname circuit breaker (module singleton) |
| `modules/secrets_manager.py` | `secrets_manager` | JWT key rotation with grace-period verification |
| `modules/cache.py` | `create_cache_backend()` | In-memory or Redis cache |
| `modules/rate_limiter.py` | `create_rate_limiter()` | Per-IP sliding-window rate limiter |
| `modules/summarizer.py` | `Summarizer` / `ExtractiveSummarizer` | TF-IDF extractive or dispatches to Gemini |
| `modules/gemini_summarizer.py` | `GeminiSummarizer` | Gemini API; truncates to `max_input_chars` |

### Security invariants (do not break)

1. **SSRF protection:** `_check_ssrf(url)` must be called before every outbound HTTP request. It blocks private/loopback/metadata CIDRs.
2. **No WAF bypass:** `web_scraper.py` is plain HTTP only — no stealth headers, proxy rotation, or Cloudflare bypass.
3. **SSL always verified:** `verify=True` on all `requests` calls.
4. **Download path traversal guard:** `validate_download_path()` in `presentation/blueprints/helpers.py` resolves and checks the path stays inside `config.output.output_dir`.
5. **Cache clear auth:** `POST /api/limpar-cache` requires JWT + admin role check via `is_admin_request()`.
6. **Admin-only routes:** `PUT /api/settings`, `POST /api/admin/rotate-secret` check `user.can_manage_system()` (only `UserRole.ADMIN`).
7. **CSP nonce:** Each request gets a fresh nonce in `g.csp_nonce` injected into the `Content-Security-Policy` header.

### Test suite

| File | What it covers |
|---|---|
| `tests/test_ssrf.py` | SSRF protection (private IPs, link-local, IPv6) |
| `tests/test_config.py` | Config attribute correctness |
| `tests/test_summarizer.py` | Extractive TF-IDF summariser |
| `tests/test_text_processor.py` | Text cleaning and tokenisation |
| `tests/test_api.py` | Flask API integration (agent mocked) |
| `tests/test_app_utils.py` | URL validation/normalisation helpers |
| `tests/test_runtime_services.py` | Circuit breaker, rate limiter, cache |
| `tests/test_db_integration.py` | Repository + ORM (requires `pytest-postgresql`) |
| `tests/test_pipeline_integration.py` | End-to-end pipeline (mocked network) |
| `tests/test_web_scraper_integration.py` | Scraper (mocked network) |

Modules excluded from coverage (require real network/browser/API): `web_scraper.py`, `selenium_scraper.py`, `file_manager.py`, `gemini_summarizer.py`.

## MCP Servers

| Server | Use case | Example tasks |
|---|---|---|
| **context7** | Fetch up-to-date library docs | Flask, SQLAlchemy, Celery, RabbitMQ documentation |
| **Ref** | Alternative library/API docs lookup | Check Flask-JWT-Extended or Alembic API reference |
| **sequential-thinking** | Complex multi-step reasoning/planning | Planning refactor strategy or migration approach |
| **exa** | Web search for current information | Search for RabbitMQ best practices, Python patterns |
| **firecrawl** | Scrape/crawl web pages for research | Fetch blog posts, documentation pages for context |
| **playwright** | Browser automation for E2E tests | Run end-to-end tests against the running app |
| **chrome-devtools** | Browser DevTools automation | Inspect network requests, debug frontend issues |
| **notebooklm** | Research compilation and summarization | Compile research notes, summarize documentation |
| **magic-mcp** | Generate UI components from natural language | Create React components from descriptions |
| **shadcn-ui** | Fetch shadcn/ui component source and demos | Get Button, Card, Table component implementations |
| **magicuidesign** | Browse and fetch UI component registry | Search animated UI components for the frontend |
| **stitch** | Design screen prototypes | Prototype new UI screens before implementing |
| **supabase** | Supabase DB operations | Future: migrate to Supabase for managed Postgres |
| **netlify** | Netlify deploy/project management | Deploy frontend builds, manage edge functions |
| **awslabs-docs** | AWS official documentation search/read | Search AWS docs for Lambda, SQS, DynamoDB patterns |
| **awslabs-cfn** | Create/update AWS CloudFormation resources | Provision S3 buckets, SQS queues via CloudFormation |
| **awslabs-iam** | AWS IAM user/role/policy management | Create IAM roles for Lambda, manage access policies |
| **awslabs-dynamodb** | DynamoDB schema design and modeling | Design task storage schema for DynamoDB migration |
| **awslabs-lambda** | Invoke AWS Lambda functions | Trigger Lambda for async summarization processing |

## Specialized Agents

| Agent | Domain | When to invoke |
|---|---|---|
| **Explore** | Codebase search | Finding files, patterns, understanding structure |
| **Plan** | Architecture design | Designing implementation approaches before coding |
| **backend-architect** | Flask/Python backend | API endpoints, services, Clean Architecture patterns |
| **postgres-architect** | DB schema | Migrations, queries, indexes, schema changes |
| **lucas-frontend-engineer** | React/TypeScript | Components, pages, state management, routing |
| **qa-engineer** | Tests | Test strategy, coverage gaps, test plans before PRs |
| **devops-deploy-architect** | Docker/CI/CD | Dockerfile, GitHub Actions, Render/cloud deployment |
| **sre-observability** | Metrics/logging | Prometheus, Grafana dashboards, correlation IDs |
| **security-hardening-validator** | Security | After adding auth endpoints, file uploads, or admin routes |
| **dx-docs-writer** | Documentation | README, SECURITY.md, ARCHITECTURE.md updates |
| **code-quality-reviewer** | Code review | After significant code changes before merging |
| **architecture-advisor** | Architecture decisions | Refactoring, introducing new patterns, tech choices |
| **tech-lead-orchestrator** | Technical leadership | End-to-end feature production readiness review |
| **llm-integration-architect** | LLM/AI integration | Gemini, prompt engineering, AI production hardening |
| **product-growth-advisor** | Growth/conversion | Funnel analysis, feature adoption optimization |
| **claude-code-guide** | Claude API/SDK | Using Anthropic SDK, Claude API integration |
| **general-purpose** | Everything else | Research, multi-step tasks, exploration |
