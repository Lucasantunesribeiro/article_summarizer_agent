# Audit Report: Article Summarizer Agent

**Date:** 2026-02-26
**Auditor:** Claude Code
**Scope:** Full codebase audit — security, architecture, correctness, performance, developer experience, testing, deployment readiness

---

## Executive Summary

The Article Summarizer Agent is a Flask-based web application that wraps a five-step content-extraction and summarization pipeline. The codebase demonstrates a clear architectural vision with well-separated modules, threading-based async task processing, and support for multiple output formats. However, the application **cannot run in its current state**: the central `config.py` module uses Portuguese attribute names while every consuming module uses English names, causing `AttributeError` failures at runtime before any request is processed.

Beyond the critical config mismatch, two of the three most serious issues concern security. The scraping layer (`web_scraper.py` and `selenium_scraper.py`) was built around WAF and Cloudflare bypass techniques, including `undetected-chromedriver`, JS fingerprint spoofing, browser profile rotation, and human-behaviour simulation. This code violates project policy and must be removed. Additionally, the application accepts arbitrary user-supplied URLs with no SSRF filtering, no content-size cap, disabled SSL certificate verification, and no rate limiting—a combination that creates significant server-side risks.

Two further structural issues are notable. The `main.py` `ArticleSummarizerAgent.run()` method accepts only `url` as an argument, but `app.py` calls it as `agente.run(url, method=metodo, length=tamanho)`, which will raise `TypeError` on every web request. The generative summarization path depends on `facebook/bart-large-cnn` (≈2 GB), making the default configuration incompatible with free-tier hosting. These findings are all verified against source code and are documented in detail below.

---

## Findings

### CRITICAL

#### C1: Config Attribute Naming Mismatch — Runtime Crash

- **Impact:** The application cannot start a successful request. Any code path that reads config values crashes immediately.
- **Evidence:**
  - `config.py` exposes `config.extracao`, `config.sumarizacao`, `config.saida`, `config.processamento`, `config.log`, `config.modelo`.
  - `main.py` references `config.summarization.method` (line 219), `config.logging.level` (line 305), `config.logging.console_enabled` (line 313), `config.logging.file_enabled` (line 321), `config.logging.log_file` (line 323), `config.output.formats` (line 255), `config.output.cache_enabled` (line 341).
  - `web_scraper.py` line 24 imports `CONTENT_SELECTORS, UNWANTED_SELECTORS` from `config`; these constants are defined in `config.py` as `SELETORES_CONTEUDO` and `SELETORES_INDESEJADOS` — the import fails immediately.
  - The same English naming pattern is present in `summarizer.py` (`config.summarization.method`), `file_manager.py` (`config.output.*`), and `text_processor.py` (`config.processing.*`).
- **Recommendation:** Rewrite `config.py` to use English attribute names matching module expectations: `config.scraping`, `config.summarization`, `config.output`, `config.processing`, `config.logging`, `config.model`. Rename module-level constants to `CONTENT_SELECTORS`, `UNWANTED_SELECTORS`, `SUPPORTED_FORMATS`, `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE`.
- **Effort:** Medium

---

#### C2: WAF / Cloudflare Bypass Code

- **Impact:** Violates project policy. Introduces prohibited dependencies (`undetected-chromedriver`, `cloudscraper`, `fake-useragent`) and legally/ethically problematic behaviour.
- **Evidence:**
  - `modules/selenium_scraper.py` docstring: *"Uses browser automation to bypass sophisticated WAF protections."* The class `AdvancedSeleniumScraper` implements stealth browser profiles, JS fingerprint injection, human-simulation (random mouse movements, scroll delays), and timezone/canvas spoofing.
  - `modules/web_scraper.py` docstring: *"Enhanced with Advanced WAF Bypassing Techniques + Selenium Integration."* The class creates rotating browser fingerprint profiles, disables SSL verification to avoid TLS fingerprinting, implements Cloudflare challenge detection, and behavioural delay simulation.
  - `requirements.txt` lists `undetected-chromedriver>=3.5.4`, `cloudscraper>=1.2.71`, `fake-useragent>=1.4.0`.
- **Recommendation:** Delete `modules/selenium_scraper.py` entirely. Rewrite `modules/web_scraper.py` to use plain `requests` + `BeautifulSoup` with legitimate headers and no bypass logic. If JS rendering is required for legitimate use cases, replace with a simple headless Selenium instance (standard `chromedriver`, no stealth options).
- **Effort:** Medium

---

#### C3: `main.py` `run()` Signature Mismatch — TypeError on Every Web Request

- **Impact:** Every request submitted through the web UI fails with `TypeError: run() got an unexpected keyword argument 'method'`.
- **Evidence:**
  - `app.py` line 287–291: `resultado = agente.run(url, method=metodo, length=tamanho)`
  - `main.py` line 53: `def run(self, url: str) -> Dict:` — the method signature accepts only `url`.
  - There is no `**kwargs` or optional `method`/`length` parameter.
- **Recommendation:** Update `run()` to accept `method: str = None` and `length: str = None`. Inside the method, apply those values to the local config before executing the pipeline, or pass them directly to the summarizer step.
- **Effort:** Low

---

### HIGH

#### H1: No SSRF Protection

- **Impact:** An attacker can supply internal network URLs (`http://127.0.0.1/`, `http://10.0.0.1/`, `http://169.254.169.254/latest/meta-data/`) to probe internal services or read cloud instance metadata.
- **Evidence:** `app.py` `validar_url()` (lines 117–137) checks only that the URL has a scheme and netloc — it does not block private IP ranges. `web_scraper.py` makes the HTTP request without any pre-flight IP resolution check.
- **Recommendation:** Before issuing any HTTP request, resolve the hostname to an IP address and reject RFC 1918 ranges (10.x, 172.16–31.x, 192.168.x), loopback (127.x), link-local (169.254.x), and `::1`. Enforce HTTPS-only URLs.
- **Effort:** Low

---

#### H2: SSL Certificate Verification Disabled

- **Impact:** All HTTPS connections are vulnerable to man-in-the-middle interception. Sensitive content and credentials passed over TLS are exposed.
- **Evidence:** `modules/web_scraper.py` creates a custom SSL context with `context.verify_mode = ssl.CERT_NONE` and `context.check_hostname = False`. This is explicitly done to avoid TLS fingerprinting by WAF systems.
- **Recommendation:** Remove the custom SSL context. Use the default `requests` session SSL behaviour (`verify=True`). Do not suppress `InsecureRequestWarning`.
- **Effort:** Low

---

#### H3: No Rate Limiting

- **Impact:** Any client can submit unlimited summarization requests, exhausting CPU, memory, and any downstream API quotas (Gemini, HuggingFace).
- **Evidence:** All Flask routes in `app.py` have no rate limiting middleware. `pip` list and `requirements.txt` do not include `flask-limiter` or any equivalent.
- **Recommendation:** Add `flask-limiter` with a Redis or in-memory backend. Apply a per-IP limit on `POST /api/sumarizar` (e.g. 10 requests per minute). Apply a lower limit on `POST /api/limpar-cache`.
- **Effort:** Low

---

### MEDIUM

#### M1: No Content-Size Limit

- **Impact:** A URL pointing to a large file (multi-GB binary, infinite stream) causes unbounded memory allocation, leading to OOM or process kill.
- **Evidence:** `web_scraper.py` calls `response.text` or `response.content` without streaming and without checking `Content-Length` first. No `max_content_length` is set in the Flask app config.
- **Recommendation:** Set `app.config['MAX_CONTENT_LENGTH']` for request bodies. In the scraper, use streaming download and abort after a configurable byte threshold (e.g. 5 MB).
- **Effort:** Low

---

#### M2: BART / Transformers Dependency — Incompatible with Free Tiers

- **Impact:** The default generative summarizer loads `facebook/bart-large-cnn`, a ~2 GB model. This exceeds RAM limits on Render free tier (512 MB) and most free cloud options. Model download also takes several minutes on cold start.
- **Evidence:** `config.py` `ConfiguracaoModelo.nome_modelo = "facebook/bart-large-cnn"`. `requirements.txt` lists `transformers>=4.30.0` and `torch>=2.0.0`.
- **Recommendation:** For the post-refactor architecture, replace the generative path with Google Gemini API (`google-generativeai`). Keep extractive TF-IDF as the offline fallback. Remove `transformers` and `torch` from `requirements.txt` to reduce Docker image size and startup time.
- **Effort:** Medium

---

#### M3: No Test Suite

- **Impact:** Regressions are undetected. The only test files (`test_advanced_waf_bypass.py`, `test_datacamp_selenium.py`, `test_datacamp_waf.py`) are manual integration scripts that test WAF bypass functionality — which is being removed.
- **Evidence:** No `pytest` in `requirements.txt`. No test directory with unit tests. `tests/` directory exists but is empty.
- **Recommendation:** Add `pytest` and `pytest-cov`. Write unit tests for: URL validation + SSRF blocking, text processing (tokenisation, sentence filtering), extractive summarisation scoring, file manager cache read/write, and the Flask API endpoints (using `app.test_client()`).
- **Effort:** High

---

#### M4: Unauthenticated Cache-Clear Endpoint

- **Impact:** Any external client can repeatedly call `POST /api/limpar-cache` to evict all cached results, forcing expensive reprocessing on every subsequent request.
- **Evidence:** `app.py` lines 685–723: `api_limpar_cache()` has no authentication check and no rate limiting. The docstring itself notes: *"PRODUÇÃO: Adicione autenticação aqui!"*
- **Recommendation:** Require a shared secret in the `Authorization` header, or restrict the endpoint to localhost only via middleware.
- **Effort:** Low

---

### LOW

#### L1: Mixed Language Codebase

- **Impact:** Increases cognitive overhead for contributors and makes automated tooling (linters, i18n, documentation generators) inconsistent.
- **Evidence:** `config.py` is entirely in Portuguese (variable names, docstrings, comments). `main.py`, `app.py`, and all `modules/*.py` are in English. Template files (`templates/*.html`) mix both languages.
- **Recommendation:** Standardise on English for all code identifiers and docstrings. User-facing text in templates should use an i18n library if multilingual support is needed.
- **Effort:** High

---

#### L2: In-Memory Task State Lost on Restart

- **Impact:** All in-progress and completed tasks are lost on every process restart or crash. Users cannot retrieve previously computed summaries after a deployment.
- **Evidence:** `app.py` lines 101–104 store `tarefas_ativas` and `resultados_tarefas` as plain Python dicts in global scope.
- **Recommendation:** Persist task state to a database (SQLite is sufficient for a single-instance deployment, Redis for multi-instance). The app.py docstring already notes this: *"Para produção, considere usar Celery + Redis."*
- **Effort:** Medium

---

## Positive Findings

- Good separation of concerns: scraper, text processor, summarizer, file manager, and orchestrator are all in distinct modules.
- Proper threading and `threading.Lock()` in `app.py` ensures thread-safe access to the shared task dictionaries.
- Cache invalidation is implemented with a 24-hour TTL in `file_manager.py`.
- Retry logic with exponential backoff is present in the web scraper.
- Multiple output formats (txt, md, json) are supported and cleanly separated in `file_manager.py`.
- Extractive TF-IDF summarisation is fully self-contained — no API key required and no large model download.
- Flask error handlers for 404 and 500 return JSON for `/api/*` paths and HTML for browser paths, which is correct.
- `SECRET_KEY` enforcement: the app refuses to start in non-debug mode without an explicit `SECRET_KEY` environment variable.

---

## Remediation Priority

| Issue | Severity | Effort | Priority |
|---|---|---|---|
| C1: Config naming mismatch | CRITICAL | Medium | 1 |
| C3: `run()` signature mismatch | CRITICAL | Low | 2 |
| C2: WAF bypass code | CRITICAL | Medium | 3 |
| H1: No SSRF protection | HIGH | Low | 4 |
| H2: SSL verification disabled | HIGH | Low | 5 |
| H3: No rate limiting | HIGH | Low | 6 |
| M4: Unauthenticated cache-clear | MEDIUM | Low | 7 |
| M1: No content-size limit | MEDIUM | Low | 8 |
| M2: BART/Transformers on free tier | MEDIUM | Medium | 9 |
| M3: No test suite | MEDIUM | High | 10 |
| L2: In-memory task state | LOW | Medium | 11 |
| L1: Mixed language codebase | LOW | High | 12 |

---

## Compliance Notes

This project's policy explicitly prohibits WAF evasion and Cloudflare bypass code. Finding C2 must be resolved before any deployment. The following files and packages must be removed or replaced:

- **Delete:** `modules/selenium_scraper.py`
- **Rewrite:** `modules/web_scraper.py` — remove all WAF bypass logic, SSL disablement, browser fingerprint rotation, and human-simulation delays
- **Remove from `requirements.txt`:** `undetected-chromedriver`, `cloudscraper`, `fake-useragent`
- **Remove test files:** `test_advanced_waf_bypass.py`, `test_datacamp_selenium.py`, `test_datacamp_waf.py`

Selenium may be retained **only** as a legitimate JavaScript-rendering fallback using standard `chromedriver` with no stealth options.
