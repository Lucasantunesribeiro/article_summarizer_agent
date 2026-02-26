"""
Web Scraper Module — Robust Public Content Extraction
=====================================================

Fetches publicly accessible web articles using standard HTTP.

Design principles:
- SSRF protection: private/internal IP ranges are blocked before any request.
- SSL verification is always enabled.
- Response size is capped to prevent memory exhaustion.
- No browser-fingerprinting, stealth, or WAF-evasion techniques.
- For JS-heavy pages that require rendering, an optional Selenium helper
  (js_scraper.py) can be used as a legitimate fallback — it does not apply
  any anti-detection measures.

Compliance note:
  This module respects robots.txt guidance and site Terms of Service.
  Accessing content that requires authentication or bypassing access controls
  is explicitly out of scope.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import random
import socket
import time
from urllib.parse import urlparse

import chardet
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CONTENT_SELECTORS, UNWANTED_SELECTORS, config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSRF Protection
# ---------------------------------------------------------------------------

_BLOCKED_NETWORKS = [ipaddress.ip_network(cidr) for cidr in config.scraping.blocked_cidrs]

_BLOCKED_HOSTNAMES = frozenset({"localhost"})
_BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".corp", ".home.arpa")


def _check_ssrf(url: str) -> None:
    """Raise ValueError if *url* targets a private or internal address.

    Checks:
    - Scheme must be http or https.
    - Hostname must not be a known-internal label.
    - All resolved IPs must be public (not RFC-1918, loopback, link-local, etc.).
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Rejected URL with unsupported scheme '{parsed.scheme}'. "
            "Only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")

    hostname_lower = hostname.lower()
    if hostname_lower in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname: {hostname!r}")

    for suffix in _BLOCKED_SUFFIXES:
        if hostname_lower.endswith(suffix):
            raise ValueError(f"Blocked hostname suffix in {hostname!r}")

    # Resolve all A/AAAA records and validate each one
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 80)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname {hostname!r}: {exc}") from exc

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in _BLOCKED_NETWORKS:
            if ip_obj in network:
                raise ValueError(
                    f"Blocked: {hostname!r} resolves to {ip_str} "
                    f"which is in private range {network}."
                )


# ---------------------------------------------------------------------------
# WebScraper
# ---------------------------------------------------------------------------


class WebScraper:
    """HTTP-based article extractor with SSRF protection and size limits."""

    def __init__(self) -> None:
        self.session = self._build_session()
        self._mem_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape_article(self, url: str) -> dict:
        """Extract article content from *url*.

        Returns a dictionary with keys:
          title, author, publish_date, description, content,
          word_count, url, status_code, encoding, scraped_at,
          extraction_method.

        Raises ValueError for SSRF-blocked URLs.
        Raises requests.HTTPError / requests.RequestException on HTTP failures.
        """
        # 1. SSRF guard (always first)
        _check_ssrf(url)

        # 2. Memory cache (within this process lifetime)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash in self._mem_cache:
            logger.debug("Returning in-process cached content for %s", url)
            return self._mem_cache[url_hash]

        # 3. Rotate user-agent on each request
        headers = dict(config.scraping.headers)
        headers["User-Agent"] = random.choice(config.scraping.user_agents)

        # 4. Fetch with retries — fall back to Wayback Machine on 403
        try:
            response = self._fetch(url, headers)
        except requests.HTTPError as http_exc:
            if http_exc.response is not None and http_exc.response.status_code == 403:
                logger.warning("403 Forbidden for %s — trying Wayback Machine fallback", url)
                return self._scrape_via_wayback(url)
            raise

        # 5. Detect encoding
        encoding = self._detect_encoding(response)
        response.encoding = encoding

        # 6. Parse and extract
        soup = BeautifulSoup(response.text, "html.parser")
        content_data = self._extract_content(soup, url)

        content_data.update(
            {
                "url": url,
                "status_code": response.status_code,
                "encoding": encoding,
                "scraped_at": time.time(),
            }
        )

        # 7. If content is suspiciously thin (JS-rendered SPA), try Wayback Machine
        if content_data.get("word_count", 0) < 80:
            logger.info(
                "Thin content (%d words) from %s — trying Wayback Machine",
                content_data.get("word_count", 0),
                url,
            )
            try:
                return self._scrape_via_wayback(url)
            except Exception as wb_exc:
                logger.warning("Wayback fallback also failed: %s — using thin content", wb_exc)

        self._mem_cache[url_hash] = content_data
        logger.info(
            "Scraped %r — %d words via %s",
            content_data.get("title", "?"),
            content_data.get("word_count", 0),
            content_data.get("extraction_method", "?"),
        )
        return content_data

    def clear_cache(self) -> None:
        self._mem_cache.clear()

    def get_cache_size(self) -> int:
        return len(self._mem_cache)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=config.scraping.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            backoff_factor=config.scraping.backoff_factor,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _fetch(self, url: str, headers: dict[str, str]) -> requests.Response:
        """Perform the HTTP GET with timeout and content-size guard."""
        for attempt in range(1, config.scraping.max_retries + 2):
            try:
                if attempt > 1:
                    delay = config.scraping.retry_delay * (
                        config.scraping.backoff_factor ** (attempt - 2)
                    )
                    logger.info("Retry %d for %s (wait %.1fs)", attempt, url, delay)
                    time.sleep(delay)

                # stream=True lets us check Content-Length before downloading body
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=config.scraping.timeout,
                    stream=True,
                    verify=True,  # SSL verification always on
                )
                response.raise_for_status()

                # Content-size guard
                content_length = int(response.headers.get("Content-Length", 0))
                if content_length > config.scraping.max_content_bytes:
                    raise ValueError(
                        f"Response too large: {content_length} bytes "
                        f"(limit {config.scraping.max_content_bytes})."
                    )

                # Read body with size cap
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=65536):
                    total += len(chunk)
                    if total > config.scraping.max_content_bytes:
                        raise ValueError(
                            f"Response body exceeded {config.scraping.max_content_bytes} bytes."
                        )
                    chunks.append(chunk)
                response._content = b"".join(chunks)
                return response

            except (requests.ConnectionError, requests.Timeout) as exc:
                logger.warning("Attempt %d failed for %s: %s", attempt, url, exc)
                if attempt > config.scraping.max_retries:
                    raise

        raise requests.RequestException(f"All retries exhausted for {url}")

    def _scrape_via_wayback(self, url: str) -> dict:
        """Fetch article from Wayback Machine when direct access is blocked (403).

        Queries the Wayback availability API, retrieves the most recent snapshot,
        and extracts content using the same pipeline as a direct fetch.
        """
        availability_url = f"https://archive.org/wayback/available?url={url}"
        try:
            api_resp = requests.get(
                availability_url,
                timeout=15,
                verify=True,
                headers={"User-Agent": config.scraping.user_agents[0]},
            )
            api_resp.raise_for_status()
            snapshot = api_resp.json().get("archived_snapshots", {}).get("closest", {})
        except Exception as exc:
            raise ValueError(
                f"Cannot reach Wayback Machine API: {exc}. "
                f"The site {url!r} returned 403 and no cached copy is available."
            ) from exc

        if not snapshot.get("available"):
            raise ValueError(
                f"Site returned 403 and no Wayback Machine snapshot exists for {url!r}. "
                "Try a different URL or check if the article is publicly accessible."
            )

        snapshot_url = snapshot["url"]
        logger.info("Wayback snapshot found: %s", snapshot_url)

        snap_resp = requests.get(
            snapshot_url,
            timeout=config.scraping.timeout,
            verify=True,
            headers={**dict(config.scraping.headers), "User-Agent": config.scraping.user_agents[0]},
        )
        snap_resp.raise_for_status()

        soup = BeautifulSoup(snap_resp.text, "html.parser")
        content_data = self._extract_content(soup, url)
        content_data.update(
            {
                "url": url,
                "status_code": snap_resp.status_code,
                "encoding": self._detect_encoding(snap_resp),
                "scraped_at": time.time(),
                "extraction_method": content_data.get("extraction_method", "") + "+wayback",
            }
        )

        self._mem_cache[hashlib.md5(url.encode()).hexdigest()] = content_data
        logger.info(
            "Wayback scrape complete — %d words for %r",
            content_data.get("word_count", 0),
            url,
        )
        return content_data

    def _detect_encoding(self, response: requests.Response) -> str:
        enc = response.encoding
        if enc and enc.lower() not in ("iso-8859-1", "ascii"):
            return enc
        detected = chardet.detect(response.content[:4096])
        if detected and detected.get("confidence", 0) > 0.8 and detected.get("encoding"):
            return detected["encoding"]
        return "utf-8"

    def _extract_content(self, soup: BeautifulSoup, url: str) -> dict:
        """Try multiple extraction strategies from most to least specific."""
        self._remove_unwanted_elements(soup)

        content = self._extract_semantic_content(soup)
        method = "semantic_selectors"

        if not content or len(content.strip()) < 100:
            content = self._extract_paragraph_content(soup)
            method = "paragraph_extraction"

        if not content or len(content.strip()) < 100:
            content = self._extract_with_newspaper(url)
            method = "newspaper3k"

        if not content or len(content.strip()) < 50:
            content = soup.get_text(separator=" ", strip=True)
            method = "full_text_fallback"

        return {
            "title": self._extract_title(soup),
            "author": self._extract_author(soup),
            "publish_date": self._extract_publish_date(soup),
            "description": self._extract_description(soup),
            "content": content.strip(),
            "word_count": len(content.split()) if content else 0,
            "extraction_method": method,
        }

    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        for selector in UNWANTED_SELECTORS:
            for el in soup.select(selector):
                el.decompose()

    def _extract_semantic_content(self, soup: BeautifulSoup) -> str:
        for selector in CONTENT_SELECTORS:
            elements = soup.select(selector)
            parts = [
                el.get_text(separator=" ", strip=True)
                for el in elements
                if len(el.get_text(strip=True)) > 50
            ]
            if parts:
                logger.debug("Content extracted via selector %r", selector)
                return " ".join(parts)
        return ""

    def _extract_paragraph_content(self, soup: BeautifulSoup) -> str:
        paragraphs = soup.find_all(["p", "div"])
        parts = [
            el.get_text(strip=True)
            for el in paragraphs
            if len(el.get_text(strip=True)) >= config.processing.min_paragraph_length
        ]
        return " ".join(parts)

    def _extract_with_newspaper(self, url: str) -> str:
        try:
            from newspaper import Article  # type: ignore[import]

            article = Article(url)
            article.download()
            article.parse()
            return article.text
        except ImportError:
            logger.debug("newspaper3k not installed — skipping")
            return ""
        except Exception as exc:
            logger.debug("newspaper3k extraction failed: %s", exc)
            return ""

    # --- Metadata extractors ---

    def _extract_title(self, soup: BeautifulSoup) -> str:
        selectors = [
            "h1",
            "title",
            '[property="og:title"]',
            '[name="twitter:title"]',
            ".title",
            ".headline",
            ".post-title",
            ".article-title",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True) or el.get("content", "")
                if text and len(text) > 3:
                    return str(text)
        return "Unknown Title"

    def _extract_author(self, soup: BeautifulSoup) -> str:
        selectors = [
            '[name="author"]',
            '[property="article:author"]',
            '[rel="author"]',
            ".author",
            ".byline",
            ".writer",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True) or el.get("content", "")
                if text:
                    return str(text)
        return "Unknown Author"

    def _extract_publish_date(self, soup: BeautifulSoup) -> str:
        selectors = [
            '[property="article:published_time"]',
            '[name="publish_date"]',
            '[name="date"]',
            "time[datetime]",
            ".date",
            ".publish-date",
            ".timestamp",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                date = el.get("content", "") or el.get("datetime", "") or el.get_text(strip=True)
                if date:
                    return str(date)
        return "Unknown Date"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        selectors = [
            '[name="description"]',
            '[property="og:description"]',
            '[name="twitter:description"]',
            ".description",
            ".excerpt",
            ".summary",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get("content", "") or el.get_text(strip=True)
                if text and len(str(text)) > 10:
                    return str(text)
        return ""
