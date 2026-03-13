# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| main branch (latest) | Yes |
| Any tagged release | Yes (if < 6 months old) |
| Older commits | No |

Security fixes are applied only to the `main` branch. If you are running a pinned older commit, update to the latest before reporting a potential duplicate.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately by emailing the maintainer with the subject line `[SECURITY] Article Summarizer Agent`. Include:

1. A clear description of the vulnerability and the affected component.
2. Steps to reproduce (curl commands, proof-of-concept URLs, or code snippets).
3. The potential impact (what an attacker can achieve).
4. Your suggested fix or mitigation, if any.

You will receive an acknowledgement within 72 hours. We aim to release a patch within 14 days of a confirmed critical finding, and within 30 days for high/medium findings.

---

## Threat Model

The following threats are in scope. Controls implemented (or planned for post-refactor) are listed alongside each threat.

### SSRF — Server-Side Request Forgery (HIGH)

**Threat:** A user supplies a URL that resolves to an internal network address (`127.0.0.1`, `10.x.x.x`, `172.16–31.x.x`, `192.168.x.x`, `169.254.169.254` cloud metadata endpoint). The scraper fetches the internal resource on behalf of the attacker.

**Controls:**
- Before issuing any HTTP request, resolve the target hostname to an IP address.
- Reject requests where the resolved IP falls within RFC 1918 private ranges, loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), or IPv6 loopback (`::1`).
- Enforce HTTPS-only URLs (reject `http://` scheme).
- Log and alert on SSRF-blocked requests.

**Current status:** Implemented in `modules/web_scraper.py` via `_check_ssrf()`. All private, loopback, link-local, and metadata CIDRs are blocked before every outbound HTTP request.

---

### Content Injection (MEDIUM)

**Threat:** The scraped article contains malicious HTML or JavaScript that is reflected into the summary output or stored in JSON files, and later rendered in the browser without sanitisation.

**Controls:**
- Summary text is rendered via Jinja2 templates with autoescaping enabled (Flask default). Do not use `| safe` filter on user-derived content.
- JSON output files are consumed programmatically, not rendered as HTML.
- Strip all HTML tags from extracted text before passing to the summarizer (BeautifulSoup `.get_text()` is already used for extraction).

---

### Rate Abuse / Denial of Service (HIGH)

**Threat:** An attacker submits thousands of requests to `POST /api/sumarizar`, exhausting CPU (summarization is compute-intensive), memory, or downstream API quotas (Gemini API calls).

**Controls:**
- Apply per-IP rate limiting on `POST /api/sumarizar`: recommended limit is 10 requests per minute per IP.
- Apply stricter rate limiting on `POST /api/limpar-cache`: 2 requests per minute, or require an `Authorization` header with a shared secret.
- `GET /api/tarefa/<id>` polling should be limited to 60 requests per minute per IP to prevent polling storms.
- Use `flask-limiter` with a Redis storage backend in production (in-memory backend acceptable for single-instance local deployment).

**Current status:** Implemented. Per-IP sliding-window rate limiters are applied on submit, auth, polling, and admin endpoints via `modules/rate_limiter.py`. Limits are configurable at runtime via settings API.

---

### Secret Exposure (MEDIUM)

**Threat:** API keys (`GEMINI_API_KEY`, `SECRET_KEY`) or internal configuration are leaked in logs, error responses, or committed to version control.

**Controls:**
- `SECRET_KEY` must be set as an environment variable. The application refuses to start in production mode without it (enforced in `app.py`).
- `GEMINI_API_KEY` must be set as an environment variable. Never hardcode API keys in source files.
- Log sanitisation: do not log the full request body; log only the URL and task ID.
- `.gitignore` must include `.env`, `*.log`, `.cache/`, `outputs/`, and `.model_cache/`.
- Error responses to clients must not include stack traces, internal file paths, or environment variable values.

---

### Oversized Requests / OOM (MEDIUM)

**Threat:** A URL points to a very large file (multi-GB binary, a streaming endpoint, or an intentionally inflated page). The scraper loads the entire response into memory, causing OOM and process termination.

**Controls:**
- Set a maximum response size (recommended: 5 MB) enforced via streaming download with a byte counter.
- Check `Content-Length` header before downloading; abort if it exceeds the limit.
- Set Flask's `MAX_CONTENT_LENGTH` for incoming request bodies (recommended: 1 MB).
- The summarizer's text processing should truncate input beyond a configurable token limit before invoking any model.

**Current status:** Maximum response size is enforced in `modules/web_scraper.py` via `config.scraping.max_content_bytes`. The Gemini summarizer truncates input to `max_input_chars` before calling the API.

---

## Security Controls Reference

| Control | Status | Location |
|---|---|---|
| SSRF IP range blocking | Implemented | `modules/web_scraper.py` — `_check_ssrf()` |
| HTTPS-only URL enforcement | Implemented | `presentation/blueprints/api.py` |
| SSL certificate verification | Implemented (`verify=True`) | `modules/web_scraper.py` |
| Content-size limit | Implemented | `config.scraping.max_content_bytes` |
| Rate limiting | Implemented (4 profiles) | `modules/rate_limiter.py` |
| SECRET_KEY enforcement | Implemented | `presentation/app_factory.py` |
| HTML autoescaping | Implemented (Jinja2 default) | All templates |
| No stack traces in API errors | Implemented | `presentation/app_factory.py` error handlers |
| .env excluded from git | Implemented | `.gitignore` |
| WAF bypass code | Removed | Clean HTTP only |
| JWT RBAC | Implemented | `presentation/blueprints/auth.py`, `domain/entities.py` |
| JWT secret rotation with grace period | Implemented | `modules/secrets_manager.py` |
| CSP nonce per request | Implemented | `presentation/app_factory.py` — `_add_security_headers` |
| CSRF token in cookies | Implemented | Flask-JWT-Extended cookie CSRF |
| Path traversal guard | Implemented (`is_relative_to`) | `presentation/blueprints/helpers.py` |
| /metrics token auth | Implemented (`METRICS_TOKEN` env) | `presentation/blueprints/api.py` |
| Correlation ID | Implemented (`X-Request-ID`) | `presentation/app_factory.py` |
| Idempotency key deduplication | Implemented (`X-Idempotency-Key`) | `application/handlers/task_handlers.py` |
| Outbox pattern for event durability | Implemented | `infrastructure/repositories.py`, `tasks/outbox_relay.py` |
| Dead Letter Queue model | Implemented | `models.py` — `DeadLetterEntry` |
| RabbitMQ AMQP persistent broker | Implemented | `celery_app.py`, `docker-compose.yml` |
| Audit log | Implemented | `models.py` — `AuditLog`, `domain/entities.py` |

---

## Out of Scope

The following are explicitly prohibited in this project and will not be accepted in any contribution:

- **WAF evasion or bypass**: Any code whose purpose is to circumvent a website's bot-detection, rate limiting, or access control mechanisms. This includes but is not limited to: `undetected-chromedriver`, browser fingerprint spoofing, `cloudscraper`, human-behaviour simulation, rotating proxies for evasion, or Cloudflare challenge solvers.
- **Credential stuffing tools**: Code that attempts authentication with lists of credentials.
- **Scraping of sites that explicitly prohibit it**: Always check and respect the target site's `robots.txt` and Terms of Service.

Any pull request containing WAF bypass, fingerprint spoofing, or stealth scraping code will be rejected without review.
