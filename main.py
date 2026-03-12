#!/usr/bin/env python3
"""CLI entrypoint for the Article Summarizer application."""
from __future__ import annotations

import argparse
import logging
import sys

import colorama
from colorama import Fore, Style

from config import config
from infrastructure.pipeline import ArticlePipelineRunner

colorama.init()
logger = logging.getLogger("ArticleSummarizerAgent")


class ArticleSummarizerAgent(ArticlePipelineRunner):
    """Backward-compatible CLI-facing facade around the pipeline runner."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Article Summarizer Agent")
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
    parser.add_argument("--output-dir", "-o", dest="output_dir")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--status", "-s", action="store_true")
    parser.add_argument("--clear-cache", action="store_true")
    parser.add_argument("--cleanup-files", type=int, metavar="DAYS")
    return parser


def _interactive_mode() -> None:
    print(f"{Fore.CYAN}Interactive mode — enter URLs or 'quit'{Style.RESET_ALL}")
    agent = ArticleSummarizerAgent()
    while True:
        try:
            url = input(f"{Fore.GREEN}URL: {Style.RESET_ALL}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}Bye!{Style.RESET_ALL}")
            return
        if url.lower() in {"quit", "exit", "q"}:
            return
        if not url:
            continue
        result = agent.run(url)
        if result["success"]:
            print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
            print(result["summary"])
        else:
            print(f"{Fore.RED}{result.get('error', 'Unknown error')}{Style.RESET_ALL}")


def main() -> None:
    args = _build_parser().parse_args()
    config.update_from_args(args)
    agent = ArticleSummarizerAgent()

    if args.interactive:
        _interactive_mode()
        return

    if args.status:
        print(agent.get_status())
        return

    if args.clear_cache:
        agent.clear_cache()
        print(f"{Fore.GREEN}Cache cleared{Style.RESET_ALL}")
        return

    if args.cleanup_files:
        agent.file_manager.cleanup_old_files(args.cleanup_files)
        print(
            f"{Fore.GREEN}Cleaned up files older than {args.cleanup_files} days{Style.RESET_ALL}"
        )
        return

    if not args.url:
        _interactive_mode()
        return

    result = agent.run(args.url, method=args.method, length=args.length)
    if result["success"]:
        print(result["summary"])
        return

    print(f"{Fore.RED}{result.get('error', 'Unknown error')}{Style.RESET_ALL}")
    sys.exit(1)


if __name__ == "__main__":
    main()
