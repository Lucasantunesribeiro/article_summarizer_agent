"""Pipeline runner used by the application layer."""

from __future__ import annotations

import logging
import time
from typing import Any

from config import config
from modules import FileManager, Summarizer, TextProcessor, WebScraper
from modules.cache import CacheBackend, create_cache_backend

logger = logging.getLogger(__name__)


class ArticlePipelineRunner:
    """Clean application-facing pipeline runner."""

    def __init__(self, cache_backend: CacheBackend | None = None) -> None:
        self.cache_backend = cache_backend or create_cache_backend(ttl=config.output.cache_ttl)
        self.web_scraper = WebScraper()
        self.text_processor = TextProcessor()
        self.summarizer = Summarizer()
        self.file_manager = FileManager(cache_backend=self.cache_backend)

    def run(
        self,
        url: str,
        method: str | None = None,
        length: str | None = None,
    ) -> dict[str, Any]:
        effective_method = method or config.summarization.method
        effective_length = length or config.summarization.summary_length
        start = time.time()

        cached = self.file_manager.load_cached_result(url)
        if cached:
            return cached

        try:
            scraped = self.web_scraper.scrape_article(url)
            if not scraped.get("content") or len(scraped["content"].strip()) < 100:
                raise ValueError("Insufficient content extracted.")

            processed = self.text_processor.process_text(scraped["content"])
            if len(processed.get("sentences", [])) < 1:
                raise ValueError("Insufficient sentences after processing.")

            summary = self.summarizer.summarize(
                processed,
                method=effective_method,
                length=effective_length,
            )
            if not summary.get("summary"):
                raise ValueError("Generated summary is empty.")

            files = self.file_manager.save_results(summary, scraped, processed)
            result: dict[str, Any] = {
                "success": True,
                "url": url,
                "execution_time": time.time() - start,
                "summary": summary["summary"],
                "method_used": summary["method_used"],
                "files_created": files["files_created"],
                "statistics": files["summary_stats"],
                "timestamp": time.time(),
            }
            self.file_manager.save_to_cache(url, result)
            return result
        except Exception as exc:
            logger.error("Pipeline failed for %s: %s", url, exc)
            return {
                "success": False,
                "url": url,
                "error": str(exc),
                "execution_time": time.time() - start,
                "timestamp": time.time(),
            }

    def clear_cache(self) -> None:
        self.file_manager.clear_cache()
        self.web_scraper.clear_cache()

    def get_status(self) -> dict[str, Any]:
        return {
            "version": "3.0.0",
            "config": {
                "summarization_method": config.summarization.method,
                "summary_length": config.summarization.summary_length,
                "output_formats": config.output.formats,
                "cache_enabled": config.output.cache_enabled,
                "gemini_model": config.gemini.model_id,
            },
            "storage_info": self.file_manager.get_storage_info(),
            "modules_loaded": {
                "web_scraper": True,
                "text_processor": True,
                "summarizer": True,
                "file_manager": True,
            },
        }
