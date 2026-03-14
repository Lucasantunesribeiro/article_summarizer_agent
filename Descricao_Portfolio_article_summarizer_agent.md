# Article Summarizer Agent — Portfolio Description (English)

## 1. Project Overview

The `article_summarizer_agent` is a web platform for extracting, processing, and summarizing public articles. The system receives a URL, performs scraping with security protections, processes the text, generates a summary via extractive (TF-IDF) or generative (Gemini) approach, persists the history, and exposes asynchronous polling via `task_id`, artifact downloads, and an admin panel.

The dual problem it solves:

- Automate reading and condensing long content;
- Transform a potentially slow process into an asynchronous, observable, and manageable flow.

The core domain is content automation and NLP. What approximates this project to the enterprise universe is not the business itself, but the engineering structure: layered architecture, persistence, auth, security controls, async queue, cache, migrations, and an automated test suite.

**v3.1 status (2026-03-13):**
- Tests passing (including 17 new domain entity tests);
- `ruff check .`: green.

## 2. System Architecture

### Architectural Classification

The system is a **modular monolith**, not a microservices architecture. The repository organization follows **pragmatic Clean Architecture**, with influences of **light tactical DDD**, **light CQRS**, and **internal event-driven design**.

### How It Appears in Real Code

- `presentation/` concentrates the HTTP and HTML boundary with Flask Blueprints.
- `application/` contains commands, queries, and handlers modeling use cases.
- `domain/` contains entities, events, and repository contracts.
- `infrastructure/` implements SQLAlchemy persistence, auth, dependency container, runtime settings, and the pipeline runner.
- `modules/` concentrates cross-cutting technical services: scraper, text processor, summarizer, cache, rate limiter, secrets manager, circuit breaker, and Prometheus metrics.
- `tasks/` integrates async execution with Celery (summarization task + outbox relay).

### Architecture Strengths

- `presentation/app_factory.py`: clean application bootstrap, middlewares, JWT, CSP nonce, Swagger, and blueprint registration.
- `infrastructure/container.py`: wires dependencies, handlers, repositories, rate limiters, and the async dispatcher.
- `application/handlers/task_handlers.py`: separates submission, processing, querying, statistics, and download by use case.
- `domain/entities.py`: state machine with guarded transitions, `TaskId` value object, domain properties, and User lifecycle methods.

## 3. Technology Stack

### Backend

- **Python 3.10+ / 3.12 / 3.13**: application base.
- **Flask**: lightweight HTTP layer for API and server-rendered pages.
- **Flask-JWT-Extended**: JWT authentication via headers and cookies.
- **Flasgger**: Swagger UI at `/apidocs/`.

### Processing and AI

- **requests + BeautifulSoup4**: HTTP scraping and HTML parsing.
- **NLTK + langdetect**: cleaning, tokenization, stopwords, and language detection.
- **scikit-learn + numpy**: extractive summarization via TF-IDF and cosine similarity.
- **google-genai**: optional integration with Gemini for generative summarization.
- **tenacity + urllib3 Retry**: exponential retries in scraping.

### Database

- **SQLAlchemy 2**: ORM and repositories.
- **Alembic**: schema versioning and migrations (5 migrations).
- **SQLite**: fallback and simple local environment.
- **PostgreSQL**: target database for production.

### Infrastructure and Async

- **Celery**: async task execution with `task_reject_on_worker_lost=True`.
- **RabbitMQ** (v3.1): enterprise-grade AMQP broker (replaced Redis as broker).
- **Redis**: distributed cache, rate limiting, and Celery result backend.
- **Gunicorn**: WSGI server for productive runtime.
- **Docker / Docker Compose**: environment with API, worker, Postgres, Redis, RabbitMQ, Flower, Prometheus, and Grafana.
- **Flower**: Celery operational panel.

### Frontend

- **Jinja2**: server-side rendering (Python templates).
- **React 18 + TypeScript** (v3.1): SPA with React Query, React Router, and Tailwind CSS.
- **Bootstrap 5**: visual base for Jinja2 templates.
- **JavaScript vanilla**: interactions in server-side templates.

### Observability and Operations

- **prometheus_client**: `/metrics` endpoint (protected by `METRICS_TOKEN` env var).
- **Grafana** (v3.1): provisioned dashboard with 5 panels (request rate, task rate, active tasks, p50/p95 duration, error rate).
- **Correlation ID** (v3.1): `X-Request-ID` injected per request, propagated in logs and response headers.
- **python-json-logger**: structured logs with `request_id` via `RequestIdFilter`.
- **Health check** at `/health`.

### DevOps

- **GitHub Actions**: lint, tests (with PostgreSQL + RabbitMQ services), and Docker build pipeline.
- **Render**: cloud deploy manifest with web + worker services; migrations moved to build step.
- **Makefile** and `scripts/dev.ps1`: Linux/macOS/Windows development ergonomics.

## 4. System Flow

1. User sends `POST /api/sumarizar` with URL, method, and summary length. Optionally includes `X-Idempotency-Key` to prevent duplicate submissions.
2. The API normalizes the URL, validates parameters, applies rate limiting, checks idempotency key, and registers a task in the database.
3. An `OutboxEntry` is persisted atomically alongside the task record.
4. The use case publishes a `TaskSubmitted` event.
5. The dispatcher in `infrastructure/container.py` tries Celery (RabbitMQ); if no worker is available, falls back to a local thread.
6. The pipeline (`infrastructure/pipeline.py`) executes scraping, text processing, summarization, and artifact saving.
7. The result is persisted in the `tasks` table with files in `outputs/` and cache in the configured backend.
8. The client polls `GET /api/tarefa/<task_id>` until completion.
9. The Celery beat `outbox_relay` task scans pending outbox entries every 30 seconds and marks them as published.

## 5. Engineering Concepts Applied

### Clean Architecture
Real separation of `presentation`, `application`, `domain`, and `infrastructure`. API talks to handlers, handlers use contracts, persistence stays in infrastructure.

### DDD (v3.1)
- Entities: `SummarizationTask`, `User`, `AuditLogEntry`, `SettingsEntry`, `OutboxEntry`.
- Value object: `TaskId` (immutable, validated UUID).
- State machine: `_TASK_VALID_TRANSITIONS`, `TaskTransitionError`, guarded `mark_*` methods.
- User lifecycle: `activate()`, `deactivate()`, `can_manage_system()`.
- Domain events: `TaskSubmitted`, `TaskCompleted`, `TaskFailed`, `UserAuthenticated`, `CacheCleared`, `JwtSecretRotated`.

### CQRS (Light)
`application/commands.py` and `application/queries.py` separate writes and reads. Handlers in `task_handlers.py` and `admin_handlers.py` reflect this separation.

### Event-Driven (Internal + Outbox)
- Internal in-process event bus publishes and subscribes to domain events.
- **Outbox pattern** (v3.1): events are persisted atomically, then relayed by a Celery beat task — ensuring durability even if the process crashes before publishing.

### Idempotency (v3.1)
SHA-256 keyed deduplication on task submission. Non-failed tasks are returned directly on duplicate keys.

### Retry + DLQ (v3.1)
- Tenacity and urllib3 retries in scraping.
- Celery `max_retries=3` with `task_reject_on_worker_lost=True`.
- `DeadLetterEntry` ORM model for persistent failure tracking.

### Security Invariants
1. **SSRF protection**: `_check_ssrf()` blocks all private/loopback/metadata CIDRs.
2. **No WAF bypass**: plain HTTP only, no stealth headers or proxy rotation.
3. **SSL always verified**: `verify=True` on all `requests` calls.
4. **Path traversal guard**: `validate_download_path()` uses `is_relative_to()`.
5. **JWT RBAC**: admin-only routes check `user.can_manage_system()`.
6. **CSP nonce**: fresh nonce per request injected into `Content-Security-Policy`.
7. **Metrics token**: `/metrics` endpoint protected by `METRICS_TOKEN` bearer token.
8. **Correlation ID**: `X-Request-ID` propagated through request lifecycle.

## 6. Market Checklist

| Market Requirement | Present | Notes |
|---|---|---|
| API REST | Yes | Flask Blueprints with clear HTTP routes |
| PostgreSQL | Yes | Target database in `docker-compose.yml` |
| React / Angular | Yes (v3.1) | React 18 + TypeScript + Tailwind SPA in `frontend/` |
| Docker | Yes | `Dockerfile` and `docker-compose.yml` |
| CI/CD | Partial | GitHub Actions CI; Render deploy manifest present |
| Redis | Yes | Cache, rate limiting, result backend |
| Celery / async queue | Yes | Real async processing with fallback |
| RabbitMQ / Kafka / SQS | Yes (v3.1) | RabbitMQ AMQP broker in `celery_app.py` |
| Clean Architecture | Partial | Real structure, with `modules/` as shared services layer |
| DDD | Partial (v3.1) | Entities, events, repositories, state machine, value object |
| CQRS | Yes | Commands, queries, handlers separated |
| Event Driven | Partial (v3.1) | Internal events + outbox pattern for durability |
| Outbox Pattern | Yes (v3.1) | `OutboxEntry`, `SqlAlchemyOutboxRepository`, beat relay task |
| Idempotency | Yes (v3.1) | `X-Idempotency-Key` → `tasks.idempotency_key` (SHA-256) |
| Retry | Yes | Tenacity in scraper, Celery task retries |
| DLQ | Yes (v3.1) | `DeadLetterEntry` model + migration |
| API Security | Yes | JWT, RBAC, CSRF, SSRF, CSP, rate limiting, path traversal guard |
| Automated tests | Yes | Strong suite with unit and integration tests |
| Observability | Yes (v3.1) | Prometheus instrumented, Grafana provisioned, correlation ID |
| Prometheus / Grafana | Yes (v3.1) | Full stack in `docker-compose.yml` + provisioned dashboard |

## 7. How to Explain in an Interview

### Simple Explanation (30 seconds)

I built a platform that receives public article links, extracts the content, generates summaries, and processes everything asynchronously. The focus was not just the functionality, but building a production-closer backend with persistence, JWT auth, rate limiting, cache, Docker, tests, and layered architecture. In v3.1, I added RabbitMQ as the broker, implemented the outbox pattern, idempotency, a full Prometheus/Grafana observability stack, a React/TypeScript frontend, and enriched the domain entities with a state machine.

### Technical Explanation (2 minutes)

The project is a modular monolith in Flask organized in `presentation`, `application`, `domain`, and `infrastructure`, with a technical layer in `modules/` for scraper, NLP, cache, and security. Submission creates a task persisted in the database, writes an outbox entry atomically, publishes an internal `TaskSubmitted` event, and a dispatcher sends processing to Celery with RabbitMQ, or falls back to a local thread. The pipeline executes scraping with SSRF protection, retry, and circuit breaker, processes text with NLTK/langdetect, summarizes via TF-IDF or Gemini, and persists result and artifacts. The outbox relay Celery beat task scans pending entries every 30 seconds for reliable event delivery. The `X-Idempotency-Key` header prevents duplicate task creation. The domain layer has a proper state machine with guarded transitions. Prometheus metrics are instrumented in the request lifecycle and task handlers, with a Grafana dashboard provisioned. The React/TypeScript SPA uses React Query for polling and React Router for navigation.

## 8. Final Score

**Score: 7.8 / 10** (v3.1 — updated 2026-03-13)

### What raises the score:
- More mature architecture than average portfolio projects.
- Real concern for security, operations, and tests.
- Async processing, persistence, cache, auth, migrations, CI, and Docker.
- RabbitMQ, outbox pattern, idempotency, DLQ — enterprise integration maturity.
- Prometheus/Grafana observability stack with instrumented metrics.
- React/TypeScript frontend demonstrating full-stack capability.

### What still limits the score:
- Core stack is Python/Flask, not .NET/React/AWS (career target alignment).
- Event-driven is still mostly internal; no external service-to-service messaging.
- No Kubernetes manifests, Terraform, or IaC.
- Domain is functional/automation, not typical enterprise business domain.
- C# / ASP.NET Core / EF Core absent (largest gap for .NET-target positions).
