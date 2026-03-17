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

| Server | Use case | When to invoke |
|---|---|---|
| **context7** | Fetch up-to-date library docs | **Invoke when:** about to write code using a specific library API (Flask, SQLAlchemy, Celery, Alembic, kombu) and the version matters, OR when hitting an AttributeError/ImportError that suggests the API changed. **Do NOT use** for general Python questions. |
| **Ref** | Alternative library/API docs lookup | **Invoke when:** context7 doesn't have the library, OR when checking Flask-JWT-Extended, Pydantic, or Alembic API reference specifically. |
| **sequential-thinking** | Complex multi-step reasoning | **Invoke when:** planning a refactor that touches 3+ layers, designing a migration strategy, or decomposing an ambiguous large task before writing any code. |
| **exa** | Current web search | **Invoke when:** looking for RabbitMQ best practices, Python patterns not in docs, security advisories, or confirming a library's latest version. |
| **firecrawl** | Scrape/crawl web pages | **Invoke when:** fetching a blog post, GitHub issue, or documentation page that isn't in standard docs (e.g., a Celery recipe from a community article). |
| **playwright** | Browser automation / E2E | **Invoke when:** running end-to-end tests against the running app at localhost:5000, or verifying that a UI change works in a real browser. |
| **chrome-devtools** | Browser DevTools automation | **Invoke when:** debugging frontend network requests, inspecting CSP violations, checking React hydration errors, or auditing Lighthouse performance. |
| **magic-mcp** | Generate UI components | **Invoke when:** creating a new React component from a natural-language description (e.g., "a card that shows task status with a progress bar"). |
| **shadcn-ui** | shadcn/ui component source | **Invoke when:** implementing a new shadcn/ui component (Button, Card, Table, Dialog) — fetch the source instead of writing from scratch. |
| **magicuidesign** | Animated UI component registry | **Invoke when:** looking for animated or interactive UI components beyond shadcn/ui defaults (e.g., animated counters, shimmer loaders). |
| **stitch** | Design screen prototypes | **Invoke when:** prototyping a new page before writing React code — useful for quickly validating layout ideas. |
| **supabase** | Supabase DB operations | **Invoke when:** migrating to Supabase-managed Postgres, or using Supabase Auth/Storage in future features. |
| **netlify** | Netlify deploy/project management | **Invoke when:** deploying the frontend build to Netlify, managing edge functions, or checking deploy status. |
| **awslabs-docs** | AWS official documentation | **Invoke when:** researching AWS service patterns (Lambda, SQS, ECS, RDS, ElastiCache) — use before writing any AWS-specific code or IaC. |
| **awslabs-cfn** | AWS CloudFormation CRUD | **Invoke when:** provisioning or updating AWS resources (S3, SQS, RDS, ECS) via CloudFormation — use after awslabs-docs to understand the resource schema. |
| **awslabs-iam** | AWS IAM management | **Invoke when:** creating IAM roles for Lambda/ECS, managing policies for CI/CD pipelines, or auditing permissions. |
| **awslabs-dynamodb** | DynamoDB schema design | **Invoke when:** designing or validating a DynamoDB data model — use before writing any DynamoDB access code. |
| **awslabs-lambda** | Invoke AWS Lambda | **Invoke when:** triggering a Lambda function for async summarization or testing a deployed Lambda directly. |

## Specialized Agents

| Agent | Domain | When to invoke |
|---|---|---|
| **Explore** | Codebase search | **Invoke when:** searching for a file/pattern across the repo and a simple Glob/Grep won't be sufficient (e.g., "find all places that call circuit_breaker" across 5+ directories). Use for open-ended codebase exploration. |
| **Plan** | Architecture design | **Invoke when:** about to implement a feature that touches 3+ files/layers — always plan before coding to validate approach. Skip only for trivial single-file changes. |
| **backend-architect** | Flask/Python backend | **Invoke when:** (1) adding or modifying API endpoints in `presentation/blueprints/`, (2) changing handlers in `application/`, (3) modifying infrastructure adapters, (4) designing new domain entities or repository contracts. |
| **postgres-architect** | DB schema | **Invoke when:** (1) creating or modifying Alembic migrations, (2) adding/removing columns or indexes, (3) optimizing a slow query, (4) designing a new table relationship. |
| **lucas-frontend-engineer** | React/TypeScript | **Invoke when:** (1) adding or modifying files under `frontend/src/`, (2) fixing React component logic or hooks, (3) creating new pages or shared components, (4) updating Vite config or Tailwind setup. Do NOT invoke for backend API changes. |
| **qa-engineer** | Tests | **Invoke when:** (1) a new feature is complete and needs test coverage, (2) before opening a PR to verify no gaps, (3) designing test strategy for a complex flow (e.g., outbox + Celery + RabbitMQ). |
| **devops-deploy-architect** | Docker/CI/CD | **Invoke when:** (1) modifying `Dockerfile`, `docker-compose.yml`, `render.yaml`, or GitHub Actions, (2) adding a new service to the stack, (3) changing build or deployment scripts. |
| **sre-observability** | Metrics/logging/tracing | **Invoke when:** (1) adding new Prometheus metrics, (2) wiring OpenTelemetry instrumentation, (3) designing Grafana dashboards or SLOs, (4) improving structured logging or request correlation. |
| **security-hardening-validator** | Security | **Invoke when:** (1) adding or modifying any auth/JWT endpoint, (2) adding file upload or admin routes, (3) changing CORS or CSP configuration, (4) any change that touches `_check_ssrf()` or rate limiting. |
| **dx-docs-writer** | Documentation | **Invoke when:** (1) a new feature is complete, (2) adding new env vars or deployment steps, (3) README/ARCHITECTURE.md is out of sync with the code. |
| **code-quality-reviewer** | Code review | **Invoke when:** a significant PR is ready — run before merging to catch over-engineering, dead code, or missing error handling. |
| **architecture-advisor** | Architecture decisions | **Invoke when:** choosing between two non-trivial approaches (e.g., sync vs async, monolith vs service extraction, SQL vs NoSQL), or when introducing a new pattern into the codebase. |
| **tech-lead-orchestrator** | Production readiness | **Invoke when:** a feature is "done" but needs a final review across security + observability + error handling + tests before going to production. |
| **llm-integration-architect** | LLM/AI integration | **Invoke when:** modifying `modules/gemini_summarizer.py`, `modules/summarizer.py`, prompt templates, or adding any new LLM API call. |
| **product-growth-advisor** | Growth/conversion | **Invoke when:** analyzing funnel drop-off, improving feature adoption, or planning UX changes aimed at increasing user engagement. |
| **claude-code-guide** | Claude API/SDK | **Invoke when:** code imports `anthropic` or `@anthropic-ai/sdk`, or when using the Anthropic API, Claude Agent SDK, or tool use patterns. |
| **general-purpose** | Everything else | **Invoke when:** the task doesn't clearly match any specialist above — research, multi-step file operations, or combining multiple concerns. |

## Git Workflow

**Never commit directly to main. All changes go through Pull Requests.**

1. Create feature branch: `git checkout -b feat/short-description`
2. Commit using conventional prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
3. Push and open PR: `gh pr create --base main`
4. Merge only after CI passes.
