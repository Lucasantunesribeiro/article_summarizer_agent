"""
Article Summarizer — Centralised Configuration
===============================================

All settings live here. Modules import from this module only.
Naming is English throughout; env-vars override defaults at startup.

Usage:
    from config import config
    timeout = config.scraping.timeout

    # Override via env:
    TIMEOUT_SCRAPING=60 python main.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Sub-configurations
# ---------------------------------------------------------------------------


@dataclass
class ScrapingConfig:
    """HTTP content-fetching settings."""

    timeout: int = int(os.getenv("TIMEOUT_SCRAPING", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES_SCRAPING", "3"))
    retry_delay: float = 2.0
    backoff_factor: float = 2.0

    # Hard limit on response body to prevent memory exhaustion (bytes)
    max_content_bytes: int = 10 * 1024 * 1024  # 10 MB

    # SSRF: private / link-local / metadata CIDRs blocked before DNS lookup
    blocked_cidrs: list[str] = field(
        default_factory=lambda: [
            "127.0.0.0/8",  # loopback
            "10.0.0.0/8",  # RFC-1918 private
            "172.16.0.0/12",  # RFC-1918 private
            "192.168.0.0/16",  # RFC-1918 private
            "169.254.0.0/16",  # link-local / EC2 metadata
            "100.64.0.0/10",  # CGNAT / shared address space
            "::1/128",  # IPv6 loopback
            "fc00::/7",  # IPv6 unique local
            "fe80::/10",  # IPv6 link-local
        ]
    )

    # Circuit breaker: how many failures before opening the circuit
    circuit_breaker_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
    # Seconds the circuit stays OPEN before allowing a probe request
    circuit_breaker_timeout: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "120"))

    headers: dict[str, str] = field(default_factory=dict)
    user_agents: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.headers:
            self.headers = {
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
        if not self.user_agents:
            self.user_agents = [
                (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) "
                    "Gecko/20100101 Firefox/132.0"
                ),
            ]


@dataclass
class ProcessingConfig:
    """Text cleaning and tokenisation settings."""

    min_paragraph_length: int = 50
    min_sentence_length: int = 10
    max_sentence_length: int = 500
    remove_short_paragraphs: bool = True
    preserve_structure: bool = True
    language_detection: bool = True


@dataclass
class SummarizationConfig:
    """Summary generation settings."""

    # "extractive" always works offline; "generative" requires GEMINI_API_KEY.
    method: Literal["extractive", "generative"] = os.getenv("SUMMARIZATION_METHOD", "extractive")  # type: ignore[assignment]

    summary_length: Literal["short", "medium", "long"] = os.getenv("SUMMARY_LENGTH", "medium")  # type: ignore[assignment]

    # Extractive: sentences per length
    extractive_sentences: dict[str, int] = field(
        default_factory=lambda: {"short": 3, "medium": 5, "long": 8}
    )

    # Generative (Gemini): token budget
    max_tokens: int = 1024
    temperature: float = 0.7

    # If generative fails, fall back to extractive automatically
    use_fallback: bool = True


@dataclass
class GeminiConfig:
    """Google Gemini API settings.

    Model IDs follow the google-genai SDK naming convention.
    Verify the latest stable IDs at:
      https://ai.google.dev/gemini-api/docs/models
    """

    api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # Fast, low-latency model (default)
    model_id: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-preview-05-20")
    )

    # Higher-quality alternative — set GEMINI_MODEL_ID env var to override
    # e.g. GEMINI_MODEL_ID=gemini-2.5-pro-preview-05-06

    max_output_tokens: int = 1024
    temperature: float = 0.7

    # Truncate input to avoid large bills (characters, not tokens)
    max_input_chars: int = 30_000

    timeout: int = int(os.getenv("GEMINI_TIMEOUT", "30"))


@dataclass
class OutputConfig:
    """File output and cache settings."""

    formats: list[str] = field(default_factory=lambda: ["txt", "md", "json"])
    include_metadata: bool = True
    include_statistics: bool = True
    output_dir: str = os.getenv("OUTPUT_DIR", "outputs")

    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_dir: str = ".cache"
    # Cache TTL in seconds (default 24 h)
    cache_ttl: int = int(os.getenv("CACHE_TTL", "86400"))


@dataclass
class LoggingConfig:
    """Logging settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = os.getenv("LOG_LEVEL", "INFO")  # type: ignore[assignment]
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    log_file: str = "summarizer.log"
    console_enabled: bool = True


@dataclass
class ModelConfig:
    """Legacy HuggingFace model settings (kept for extractive fallback)."""

    model_name: str = os.getenv("HF_MODEL_NAME", "facebook/bart-large-cnn")
    device: Literal["auto", "cpu", "cuda", "mps"] = os.getenv("HF_DEVICE", "auto")  # type: ignore[assignment]
    cache_dir: str = ".model_cache"
    load_in_8bit: bool = False


# ---------------------------------------------------------------------------
# Rate-limiting config (used by app.py)
# ---------------------------------------------------------------------------


@dataclass
class RateLimitConfig:
    """Simple per-IP rate-limit settings for the Flask API."""

    # Max requests per window per IP
    max_requests: int = int(os.getenv("RATE_LIMIT_MAX", "10"))
    # Window length in seconds
    window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


# ---------------------------------------------------------------------------
# Main Config class
# ---------------------------------------------------------------------------


class Config:
    """Aggregated configuration singleton.

    Import as:
        from config import config
    """

    def __init__(self) -> None:
        self.scraping = ScrapingConfig()
        self.processing = ProcessingConfig()
        self.summarization = SummarizationConfig()
        self.gemini = GeminiConfig()
        self.output = OutputConfig()
        self.logging = LoggingConfig()
        self.model = ModelConfig()
        self.rate_limit = RateLimitConfig()

    def update_from_args(self, args: object) -> None:
        """Apply CLI argument overrides (argparse namespace)."""
        if getattr(args, "method", None):
            self.summarization.method = args.method  # type: ignore[attr-defined]
        if getattr(args, "length", None):
            self.summarization.summary_length = args.length  # type: ignore[attr-defined]
        if getattr(args, "output_dir", None):
            self.output.output_dir = args.output_dir  # type: ignore[attr-defined]


# Singleton
config = Config()


# ---------------------------------------------------------------------------
# Module-level constants (imported directly by modules)
# ---------------------------------------------------------------------------

# CSS selectors for main article content — tried in order until one works
CONTENT_SELECTORS: list[str] = [
    "article",
    '[role="main"]',
    "main",
    ".post-content",
    ".article-content",
    ".entry-content",
    ".content",
    ".post-body",
    ".article-body",
    ".story-body",
    ".text",
    "#content",
    "#main-content",
    ".main-content",
]

# Elements to strip before extracting text
UNWANTED_SELECTORS: list[str] = [
    "nav",
    "header",
    "footer",
    "aside",
    ".nav",
    ".header",
    ".footer",
    ".sidebar",
    ".advertisement",
    ".ads",
    ".ad",
    ".publicity",
    ".social-share",
    ".share-buttons",
    ".social-links",
    ".comments",
    ".comment",
    ".comment-section",
    ".related-articles",
    ".related-posts",
    ".more-stories",
    "script",
    "style",
    "noscript",
    "iframe",
    ".cookie-notice",
    ".cookie-banner",
    ".newsletter-signup",
    ".newsletter-popup",
    ".modal",
    ".popup",
]

# Supported ISO 639-1 language codes
SUPPORTED_LANGUAGES: list[str] = [
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "zh",
    "ja",
    "ko",
]

DEFAULT_LANGUAGE: str = "en"

# Output format → MIME type
SUPPORTED_FORMATS: dict[str, str] = {
    "txt": "text/plain",
    "md": "text/markdown",
    "json": "application/json",
}
