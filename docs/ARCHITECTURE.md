# Architecture: Article Summarizer Agent

## Overview

The Article Summarizer Agent is a Flask web application that accepts a URL, extracts the article text, processes it, and produces a summary. The pipeline runs asynchronously in a background thread so the HTTP request returns immediately with a task ID that the client polls for progress.

The application has two layers:

- **Web layer** (`app.py`): Handles HTTP, task lifecycle, threading, and file downloads.
- **Pipeline layer** (`main.py` + `modules/`): Executes the five-step extraction and summarization pipeline.

---

## High-Level Request Flow

```mermaid
flowchart TD
    A[User submits URL] --> B[POST /api/sumarizar]
    B --> C{SSRF check\nresolve hostname\nreject private IPs}
    C -- blocked --> D[400 Bad Request]
    C -- allowed --> E[Spawn background thread\nreturn task_id]
    E --> F[Step 1: Validate & normalise URL]
    F --> G[Step 2: Fetch content\nHTTPS request + BeautifulSoup]
    G --> H{JS required?}
    H -- no --> I[Extracted HTML text]
    H -- yes --> J[Selenium headless fallback\nstandard chromedriver, no stealth]
    J --> I
    I --> K[Step 3: TextProcessor\nclean, tokenise, detect language]
    K --> L[Step 4: Summarizer]
    L --> M{Summarization mode}
    M -- generative --> N[Gemini API\ngoogle-generativeai]
    M -- extractive --> O[TF-IDF + cosine similarity\nno API key required]
    N --> P[Summary text]
    O --> P
    P --> Q[Step 5: FileManager\nsave txt / md / json]
    Q --> R[Cache result 24h TTL]
    R --> S[Task status → concluida]
    S --> T[Client polls GET /api/tarefa/id\ndownloads via GET /api/download/id/format]
```

---

## Component Diagram

```mermaid
classDiagram
    class ArticleSummarizerAgent {
        +WebScraper web_scraper
        +TextProcessor text_processor
        +Summarizer summarizer
        +FileManager file_manager
        +run(url, method, length) Dict
        +get_status() Dict
        -_step1_validate_input()
        -_step2_scrape_content()
        -_step3_process_text()
        -_step4_summarize()
        -_step5_save_results()
    }

    class WebScraper {
        +scrape_article(url) Dict
        -_fetch_with_requests(url) Response
        -_fetch_with_selenium(url) str
        -_extract_content(html) str
        -_ssrf_check(url) bool
    }

    class TextProcessor {
        +process_text(raw_text) Dict
        -_clean_text(text) str
        -_tokenise_sentences(text) List
        -_detect_language(text) str
        -_filter_short_sentences(sentences) List
    }

    class Summarizer {
        +summarize(processed_data) Dict
        -extractive_summarizer ExtractiveSummarizer
        -gemini_summarizer GeminiSummarizer
    }

    class ExtractiveSummarizer {
        +summarize(sentences, n) List
        -_build_tfidf_matrix(sentences) ndarray
        -_score_sentences(matrix) Dict
    }

    class GeminiSummarizer {
        +summarize(text, length) str
        -_build_prompt(text, length) str
        -client GenerativeModel
    }

    class FileManager {
        +save_results(summary, scraped, processed) Dict
        +load_cached_result(url) Optional~Dict~
        +save_to_cache(url, result)
        +clear_cache()
        +get_storage_info() Dict
        -_cache_key(url) str
    }

    class Config {
        +scraping ConfigScraping
        +summarization ConfigSummarization
        +output ConfigOutput
        +processing ConfigProcessing
        +logging ConfigLogging
    }

    ArticleSummarizerAgent --> WebScraper
    ArticleSummarizerAgent --> TextProcessor
    ArticleSummarizerAgent --> Summarizer
    ArticleSummarizerAgent --> FileManager
    Summarizer --> ExtractiveSummarizer
    Summarizer --> GeminiSummarizer
    WebScraper ..> Config
    Summarizer ..> Config
    FileManager ..> Config
    TextProcessor ..> Config
```

---

## Flask API Sequence Diagram

```mermaid
sequenceDiagram
    actor Client
    participant Flask as app.py (Flask)
    participant Agent as ArticleSummarizerAgent
    participant Scraper as WebScraper
    participant Processor as TextProcessor
    participant Summarizer as Summarizer
    participant FM as FileManager

    Client->>Flask: POST /api/sumarizar {url, metodo, tamanho}
    Flask->>Flask: validar_url() + SSRF check
    Flask->>Flask: generate task_id, store in tarefas_ativas
    Flask->>Flask: spawn daemon thread
    Flask-->>Client: 200 {success: true, task_id}

    Note over Flask,FM: Background thread
    Flask->>Agent: run(url, method, length)
    Agent->>FM: load_cached_result(url)
    FM-->>Agent: None (cache miss)
    Agent->>Scraper: scrape_article(url)
    Scraper-->>Agent: {content, title, word_count, ...}
    Agent->>Processor: process_text(content)
    Processor-->>Agent: {sentences, cleaned_text, language, ...}
    Agent->>Summarizer: summarize(processed_data)
    Summarizer-->>Agent: {summary, method_used, ...}
    Agent->>FM: save_results(summary, scraped, processed)
    FM-->>Agent: {files_created: {txt: ..., md: ..., json: ...}}
    Agent->>FM: save_to_cache(url, result)
    Agent-->>Flask: {success: true, summary, files_created, ...}
    Flask->>Flask: update tarefas_ativas[task_id] → concluida

    Client->>Flask: GET /api/tarefa/{task_id}
    Flask-->>Client: 200 {status: concluida, resultado: {...}}
    Client->>Flask: GET /api/download/{task_id}/md
    Flask-->>Client: file download
```

---

## Module Responsibilities

| Module | File | Responsibility |
|---|---|---|
| Flask app | `app.py` | HTTP routing, task lifecycle, threading, CORS |
| Agent orchestrator | `main.py` | Five-step pipeline coordination, progress reporting |
| Config | `config.py` | Centralised settings, environment variable loading |
| Web scraper | `modules/web_scraper.py` | HTTP fetch, HTML parsing, content extraction, SSRF guard |
| Text processor | `modules/text_processor.py` | Text cleaning, tokenisation, language detection |
| Summarizer | `modules/summarizer.py` | Dispatches to Gemini or extractive; fallback logic |
| Extractive summarizer | `modules/summarizer.py` (inner class) | TF-IDF scoring, cosine similarity, sentence selection |
| Gemini summarizer | `modules/gemini_summarizer.py` (post-refactor) | Google Gemini API integration |
| File manager | `modules/file_manager.py` | Output file writing, cache read/write, storage info |

---

## Key Design Decisions

### 1. Two Summarization Modes

The application supports two modes selectable per-request:

- **Gemini (generative):** Calls Google Gemini API. Fast, high quality, natural language output. Requires `GEMINI_API_KEY`. Not usable offline.
- **Extractive TF-IDF (offline):** Scores sentences by TF-IDF weight and cosine similarity to the document centroid. Selects the top N sentences. No API key. No model download. Always available as fallback.

The `Summarizer` class dispatches based on the requested method. If `method=generative` is requested but the Gemini client fails (missing key, quota exceeded), it falls back to extractive automatically when `config.summarization.use_fallback=True`.

### 2. SSRF Protection Before Any HTTP Request

All URL inputs must pass an SSRF check before the scraper issues any network request. The check resolves the hostname to an IP address at the application layer and rejects private, loopback, and link-local ranges. This check runs in `app.py` before the background thread is spawned, so blocked requests never reach the scraper.

### 3. Async Task Processing via Threading

Each summarization request spawns a `daemon=True` Python thread. The Flask endpoint returns immediately with a `task_id`. The client polls `GET /api/tarefa/<task_id>` for status updates. Progress is stored in an in-memory dictionary protected by a `threading.Lock`.

**Production note:** Python threads are limited by the GIL for CPU-bound work and do not survive process restarts. For production workloads, replace the threading model with Celery workers and a Redis broker. Task state should be persisted to a database rather than in-memory dicts.

### 4. File-Based Cache

Computed summaries are cached as JSON files in `.cache/` with a SHA-256 hash of the URL as the filename. On cache hit, the full pipeline is skipped. TTL is 24 hours (checked by comparing file modification time).

**Production note:** File-based cache does not work across multiple instances. Replace with Redis for multi-instance deployments. The `FileManager` interface is designed to allow this substitution without changing the pipeline.

### 5. Selenium as Legitimate JS-Rendering Fallback

Some articles require JavaScript execution to render content (single-page apps, lazy-loaded bodies). When plain HTTP extraction yields insufficient content (< 100 characters), the scraper optionally falls back to a headless Selenium instance.

This Selenium usage is legitimate JS rendering only. It uses standard `chromedriver` with no stealth arguments, no fingerprint spoofing, and no human-behaviour simulation. WAF bypass via Selenium is explicitly prohibited — see `SECURITY.md`.

---

## Directory Structure

```
article_summarizer_agent/
├── app.py                  # Flask web application
├── main.py                 # Pipeline orchestrator (ArticleSummarizerAgent)
├── config.py               # Centralised configuration singleton
├── requirements.txt        # Python dependencies
├── Procfile                # Render/Heroku process declaration
├── runtime.txt             # Python version pin
├── SECURITY.md             # Security policy and threat model
├── modules/
│   ├── __init__.py
│   ├── web_scraper.py      # HTTP content extraction
│   ├── text_processor.py   # Text cleaning and tokenisation
│   ├── summarizer.py       # Extractive + Gemini summarizer
│   ├── gemini_summarizer.py# (post-refactor) Gemini API client
│   └── file_manager.py     # Output files and cache
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JS, images
├── outputs/                # Generated summary files (gitignored)
├── .cache/                 # File-based result cache (gitignored)
├── docs/
│   ├── ARCHITECTURE.md     # This document
│   ├── AUDIT_REPORT.md     # Security and code audit findings
│   └── DEPLOYMENT.md       # Deployment guide
└── tests/                  # Unit and integration tests
```
