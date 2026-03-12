"""Runtime application of persisted settings."""
from __future__ import annotations

from typing import Any

from config import config
from modules import Summarizer
from modules.cache import create_cache_backend
from modules.rate_limiter import create_rate_limiter


class RuntimeSettingsApplier:
    """Applies persisted settings to the live runtime without rebuilding the app."""

    def __init__(self, pipeline_runner, rate_limiters: dict[str, Any]) -> None:
        self._pipeline_runner = pipeline_runner
        self._rate_limiters = rate_limiters

    def apply(self, values: dict[str, Any]) -> None:
        rebuild_scraper_session = False
        rebuild_summarizer = False
        rebuild_cache_backend = False
        rebuild_rate_limiters = False

        for key, value in values.items():
            if key == "scraping.timeout":
                config.scraping.timeout = int(value)
            elif key == "scraping.max_retries":
                config.scraping.max_retries = int(value)
                rebuild_scraper_session = True
            elif key == "scraping.max_content_bytes":
                config.scraping.max_content_bytes = int(value)
            elif key == "summarization.default_method":
                config.summarization.method = str(value)
                rebuild_summarizer = True
            elif key == "summarization.default_length":
                config.summarization.summary_length = str(value)
            elif key == "summarization.gemini_model_id":
                config.gemini.model_id = str(value)
                rebuild_summarizer = True
            elif key == "output.cache_enabled":
                config.output.cache_enabled = bool(value)
                rebuild_cache_backend = True
            elif key == "output.cache_ttl":
                config.output.cache_ttl = int(value)
                rebuild_cache_backend = True
            elif key == "rate_limit.submit.max_requests":
                config.rate_limit.max_requests = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.submit.window_seconds":
                config.rate_limit.window_seconds = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.auth.max_requests":
                config.rate_limit.auth_max_requests = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.auth.window_seconds":
                config.rate_limit.auth_window_seconds = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.polling.max_requests":
                config.rate_limit.polling_max_requests = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.polling.window_seconds":
                config.rate_limit.polling_window_seconds = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.admin.max_requests":
                config.rate_limit.admin_max_requests = int(value)
                rebuild_rate_limiters = True
            elif key == "rate_limit.admin.window_seconds":
                config.rate_limit.admin_window_seconds = int(value)
                rebuild_rate_limiters = True

        if rebuild_scraper_session:
            self._pipeline_runner.web_scraper.session = self._pipeline_runner.web_scraper._build_session()

        if rebuild_summarizer:
            self._pipeline_runner.summarizer = Summarizer()

        if rebuild_cache_backend:
            cache_backend = create_cache_backend(ttl=config.output.cache_ttl)
            self._pipeline_runner.cache_backend = cache_backend
            self._pipeline_runner.file_manager.cache_backend = cache_backend

        if rebuild_rate_limiters:
            self._rate_limiters.clear()
            self._rate_limiters.update(
                {
                    "submit": create_rate_limiter(
                        max_requests=config.rate_limit.max_requests,
                        window_seconds=config.rate_limit.window_seconds,
                    ),
                    "auth": create_rate_limiter(
                        max_requests=config.rate_limit.auth_max_requests,
                        window_seconds=config.rate_limit.auth_window_seconds,
                    ),
                    "polling": create_rate_limiter(
                        max_requests=config.rate_limit.polling_max_requests,
                        window_seconds=config.rate_limit.polling_window_seconds,
                    ),
                    "admin": create_rate_limiter(
                        max_requests=config.rate_limit.admin_max_requests,
                        window_seconds=config.rate_limit.admin_window_seconds,
                    ),
                }
            )
