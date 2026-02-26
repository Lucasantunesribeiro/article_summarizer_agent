#!/usr/bin/env python3
"""
Article Summarizer Agent — CLI Entry Point
==========================================

Orchestrates a five-step pipeline:
  1. Validate + normalise URL
  2. Scrape article content (HTTP; JS rendering as fallback)
  3. Process text (clean, tokenise, detect language)
  4. Summarise (Gemini generative or extractive TF-IDF)
  5. Save results (txt / md / json)

Usage:
  python main.py --url "https://example.com/article"
  python main.py --url "..." --method generative --length short
  python main.py --interactive
  python main.py --status
  python main.py --clear-cache
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import colorama
from colorama import Fore, Style
from tqdm import tqdm

colorama.init()

sys.path.insert(0, str(Path(__file__).parent))

from config import config
from modules import FileManager, Summarizer, TextProcessor, WebScraper

logger = logging.getLogger("ArticleSummarizerAgent")


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class ArticleSummarizerAgent:
    """Autonomous agent that orchestrates the full summarisation pipeline."""

    def __init__(self) -> None:
        self._setup_logging()
        logger.info("Initialising Article Summarizer Agent…")

        try:
            self.web_scraper = WebScraper()
            self.text_processor = TextProcessor()
            self.summarizer = Summarizer()
            self.file_manager = FileManager()
            print(f"{Fore.GREEN}✓ Agent initialised{Style.RESET_ALL}")
        except Exception as exc:
            print(f"{Fore.RED}✗ Initialisation failed: {exc}{Style.RESET_ALL}")
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        url: str,
        method: str | None = None,
        length: str | None = None,
    ) -> dict:
        """Run the full pipeline for *url*.

        Args:
            url:    Article URL.
            method: Override config summarisation method ("extractive" / "generative").
            length: Override config summary length ("short" / "medium" / "long").

        Returns:
            Dict with keys: success, url, summary, statistics, files_created,
            method_used, execution_time, timestamp.
            On failure: success=False, error=<str>.
        """
        # Apply per-call overrides without mutating the singleton permanently
        if method:
            config.summarization.method = method
        if length:
            config.summarization.summary_length = length

        start = time.time()
        print(f"\n{Fore.CYAN}🤖 Article Summarizer Agent{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}URL: {url}{Style.RESET_ALL}\n")

        try:
            # Fast path: check persistent cache first
            cached = self.file_manager.load_cached_result(url)
            if cached:
                print(f"{Fore.GREEN}✓ Using cached result{Style.RESET_ALL}")
                return cached

            step1 = self._step1_validate(url)
            step2 = self._step2_scrape(step1)
            step3 = self._step3_process(step2)
            step4 = self._step4_summarize(step3)
            step5 = self._step5_save(step4, step2, step3)

            execution_time = time.time() - start
            result: dict = {
                "success": True,
                "url": url,
                "execution_time": execution_time,
                "summary": step4["summary"],
                "method_used": step4["method_used"],
                "files_created": step5["files_created"],
                "statistics": step5["summary_stats"],
                "timestamp": time.time(),
            }

            self.file_manager.save_to_cache(url, result)
            self._print_success(result)
            return result

        except Exception as exc:
            logger.error("Pipeline failed: %s", exc)
            print(f"{Fore.RED}✗ Pipeline failed: {exc}{Style.RESET_ALL}")
            return {
                "success": False,
                "url": url,
                "error": str(exc),
                "execution_time": time.time() - start,
                "timestamp": time.time(),
            }

    def get_status(self) -> dict:
        return {
            "version": "2.0.0",
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

    # ------------------------------------------------------------------
    # Pipeline steps (private)
    # ------------------------------------------------------------------

    def _step1_validate(self, url: str) -> dict:
        with tqdm(total=1, desc="Step 1: Validating URL", colour="blue") as pbar:
            url = url.strip()
            if not url:
                raise ValueError("Empty URL provided.")
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            pbar.update(1)
        logger.info("Step 1 complete: %s", url)
        return {"validated_url": url}

    def _step2_scrape(self, step1: dict) -> dict:
        url = step1["validated_url"]
        with tqdm(total=2, desc="Step 2: Scraping content", colour="green") as pbar:
            pbar.set_description("Fetching…")
            pbar.update(1)
            try:
                data = self.web_scraper.scrape_article(url)
            except Exception:
                # Try JS rendering as fallback
                try:
                    from modules.selenium_scraper import JsRenderingScraper  # noqa: PLC0415

                    data = JsRenderingScraper().scrape_article(url)
                except ImportError:
                    raise
            pbar.update(1)

        if not data.get("content") or len(data["content"].strip()) < 100:
            raise ValueError("Insufficient content extracted.")
        logger.info("Step 2 complete: %d words", data.get("word_count", 0))
        return data

    def _step3_process(self, scraped: dict) -> dict:
        with tqdm(total=2, desc="Step 3: Processing text", colour="yellow") as pbar:
            pbar.set_description("Cleaning text…")
            processed = self.text_processor.process_text(scraped["content"])
            pbar.update(1)
            sentences = processed.get("sentences", [])
            if len(sentences) < 2:
                raise ValueError("Insufficient sentences after processing.")
            pbar.set_description("Done.")
            pbar.update(1)
        logger.info("Step 3 complete: %d sentences", len(sentences))
        return processed

    def _step4_summarize(self, processed: dict) -> dict:
        method = config.summarization.method
        with tqdm(total=2, desc=f"Step 4: Summarising ({method})", colour="magenta") as pbar:
            pbar.set_description(f"Running {method}…")
            data = self.summarizer.summarize(processed)
            pbar.update(2)
        if not data.get("summary") or len(data["summary"].strip()) < 10:
            raise ValueError("Generated summary is too short or empty.")
        logger.info(
            "Step 4 complete: %d words via %s",
            len(data["summary"].split()),
            data.get("method_used"),
        )
        return data

    def _step5_save(self, summary: dict, scraped: dict, processed: dict) -> dict:
        with tqdm(total=1, desc="Step 5: Saving results", colour="cyan") as pbar:
            result = self.file_manager.save_results(summary, scraped, processed)
            pbar.update(1)
        logger.info("Step 5 complete: %d files", len(result.get("files_created", {})))
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _print_success(self, result: dict) -> None:
        print(f"\n{Fore.GREEN}✅ Summarisation complete{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 55}{Style.RESET_ALL}")
        preview = result["summary"][:200]
        if len(result["summary"]) > 200:
            preview += "…"
        print(f"\n{Fore.YELLOW}Summary:{Style.RESET_ALL}\n{preview}")
        stats = result["statistics"]
        print(f"\n{Fore.YELLOW}Stats:{Style.RESET_ALL}")
        print(
            f"  Words (original → summary): "
            f"{stats.get('words_original', 0)} → {stats.get('words_summary', 0)}"
        )
        cr = stats.get("compression_ratio", 0)
        print(f"  Compression: {cr:.1%}")
        print(f"  Method: {result['method_used']}")
        print(f"  Time: {result['execution_time']:.2f}s")
        print(f"\n{Fore.YELLOW}Files:{Style.RESET_ALL}")
        for fmt, path in result["files_created"].items():
            print(f"  {fmt.upper()}: {path}")

    def _setup_logging(self) -> None:
        level = getattr(logging, config.logging.level.upper(), logging.INFO)
        logging.basicConfig(level=level, format=config.logging.format, handlers=[])

        if config.logging.file_enabled:
            fh = logging.FileHandler(config.logging.log_file)
            fh.setLevel(level)
            fh.setFormatter(logging.Formatter(config.logging.format))
            logger.addHandler(fh)

        if config.logging.console_enabled:
            ch = logging.StreamHandler()
            ch.setLevel(logging.WARNING)
            ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(ch)

        logger.setLevel(level)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Article Summarizer Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--url", "-u", help="Article URL to summarise")
    parser.add_argument(
        "--method",
        "-m",
        choices=["extractive", "generative"],
        help="Summarisation method",
    )
    parser.add_argument(
        "--length",
        "-l",
        choices=["short", "medium", "long"],
        help="Summary length",
    )
    parser.add_argument(
        "--output-dir", "-o", dest="output_dir", help="Output directory for summary files"
    )
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--status", "-s", action="store_true", help="Show agent status")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cached results")
    parser.add_argument(
        "--cleanup-files", type=int, metavar="DAYS", help="Remove output files older than N days"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser


def _interactive_mode() -> None:
    print(f"{Fore.CYAN}Interactive mode — enter URLs or 'quit'{Style.RESET_ALL}")
    agent = ArticleSummarizerAgent()
    while True:
        try:
            url = input(f"{Fore.GREEN}URL: {Style.RESET_ALL}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}Bye!{Style.RESET_ALL}")
            break
        if url.lower() in ("quit", "exit", "q"):
            break
        if not url:
            continue
        result = agent.run(url)
        if not result["success"]:
            print(f"{Fore.RED}Error: {result.get('error')}{Style.RESET_ALL}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    config.update_from_args(args)

    if args.verbose:
        config.logging.level = "DEBUG"
        config.logging.console_enabled = True

    if args.interactive:
        _interactive_mode()
        return

    agent = ArticleSummarizerAgent()

    if args.status:
        status = agent.get_status()
        for key, val in status["config"].items():
            print(f"  {key}: {val}")
        return

    if args.clear_cache:
        agent.file_manager.clear_cache()
        print(f"{Fore.GREEN}Cache cleared{Style.RESET_ALL}")
        return

    if args.cleanup_files:
        agent.file_manager.cleanup_old_files(args.cleanup_files)
        print(f"{Fore.GREEN}Cleaned up files older than {args.cleanup_files} days{Style.RESET_ALL}")
        return

    if args.url:
        result = agent.run(args.url, method=args.method, length=args.length)
        if not result["success"]:
            print(f"{Fore.RED}{result.get('error', 'Unknown error')}{Style.RESET_ALL}")
            sys.exit(1)
    else:
        parser.print_help()
        print(f"\n{Fore.YELLOW}No URL given — starting interactive mode…{Style.RESET_ALL}\n")
        _interactive_mode()


if __name__ == "__main__":
    main()
