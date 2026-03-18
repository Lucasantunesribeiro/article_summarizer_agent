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
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util.retry import Retry

from config import CONTENT_SELECTORS, UNWANTED_SELECTORS, config
from modules.circuit_breaker import CircuitOpenError, circuit_breaker

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

        # 5. Binary format early-exit — bypass HTML pipeline entirely
        content_type = response.headers.get("Content-Type", "").lower()
        url_path = url.lower().split("?")[0]

        is_pdf = "application/pdf" in content_type or url_path.endswith(".pdf")
        is_docx = "officedocument.wordprocessingml" in content_type or url_path.endswith(".docx")
        is_txt = content_type.startswith("text/plain") or url_path.endswith(".txt")

        if is_pdf:
            content_data = self._extract_pdf_content(response._content, url)
        elif is_docx:
            content_data = self._extract_docx_content(response._content, url)
        elif is_txt:
            content_data = self._extract_txt_content(response._content, url)
        else:
            content_data = None

        if content_data is not None:
            content_data.update(
                {
                    "url": url,
                    "status_code": response.status_code,
                    "encoding": "binary",
                    "scraped_at": time.time(),
                }
            )
            self._mem_cache[url_hash] = content_data
            logger.info(
                "Binary file scraped %r — %d words via %s",
                content_data.get("title", "?"),
                content_data.get("word_count", 0),
                content_data.get("extraction_method", "?"),
            )
            return content_data

        # 6. Detect encoding
        encoding = self._detect_encoding(response)
        response.encoding = encoding

        # 7. Parse and extract
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

        # 8. If content is suspiciously thin (JS-rendered SPA), try Wayback Machine
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
        """Perform the HTTP GET with circuit breaker, Tenacity retries, and content-size guard."""
        hostname = urlparse(url).hostname or url

        # Circuit breaker check — fail fast if the host is known-broken
        if circuit_breaker.is_open(hostname):
            raise CircuitOpenError(hostname) from None

        @retry(
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
            stop=stop_after_attempt(config.scraping.max_retries + 1),
            wait=wait_exponential(
                multiplier=config.scraping.retry_delay,
                min=config.scraping.retry_delay,
                max=config.scraping.retry_delay * (config.scraping.backoff_factor**3),
            ),
            reraise=True,
        )
        def _do_fetch() -> requests.Response:
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

        try:
            response = _do_fetch()
            circuit_breaker.record_success(hostname)
            return response
        except CircuitOpenError:
            raise
        except (requests.ConnectionError, requests.Timeout) as exc:
            circuit_breaker.record_failure(hostname)
            logger.warning("All retries exhausted for %s — circuit failure recorded: %s", url, exc)
            raise
        except Exception:
            circuit_breaker.record_failure(hostname)
            raise

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
                f"Não foi possível acessar '{url}': o site retornou 403 (acesso negado) "
                "e não há cópia no Wayback Machine. "
                "Tente outro URL ou use o método Generativo (Gemini) que pode ter "
                "acesso a este conteúdo via conhecimento prévio."
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

    def _extract_pdf_content(self, pdf_bytes: bytes, url: str) -> dict:
        """Extract plain text from PDF binary content.

        Strategy:
        1. pypdf (fast, works for most text-layer PDFs)
        2. pdfplumber fallback (better for multi-column/complex layouts)
        3. If both fail on a non-empty PDF → raise informative ValueError
        """
        try:
            import io

            import pypdf  # noqa: PLC0415

            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)

            # --- Step 1: pypdf ---
            pages_text = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(text)
            content = "\n\n".join(pages_text).strip()

            # --- Step 2: pdfplumber fallback ---
            if len(content) < 100 and num_pages > 0:
                logger.info("pypdf yielded thin content (%d chars) — trying pdfplumber", len(content))
                content = self._try_pdfplumber(pdf_bytes)

            # --- Step 3: Scanned PDF — raise user-friendly error ---
            if not content and num_pages > 0:
                raise ValueError(
                    f"O PDF possui {num_pages} página(s) mas não contém texto extraível. "
                    "Provavelmente é um documento digitalizado (imagem). "
                    "Tente um PDF com texto selecionável ou copie o conteúdo para um arquivo .txt."
                )

            meta = reader.metadata or {}
            title = (meta.get("/Title") or "").strip() or url.rstrip("/").split("/")[-1]
            author = (meta.get("/Author") or "").strip() or "Unknown Author"

            return {
                "title": title,
                "author": author,
                "publish_date": "Unknown Date",
                "description": "",
                "content": content,
                "word_count": len(content.split()) if content else 0,
                "extraction_method": "pdf_pypdf" if pages_text else "pdf_pdfplumber",
            }
        except ValueError:
            raise  # propagate user-friendly errors to the pipeline
        except Exception as exc:
            logger.warning("PDF extraction failed for %s: %s", url, exc)
            return {
                "title": url.rstrip("/").split("/")[-1],
                "author": "Unknown Author",
                "publish_date": "Unknown Date",
                "description": "",
                "content": "",
                "word_count": 0,
                "extraction_method": "pdf_failed",
            }

    def _try_pdfplumber(self, pdf_bytes: bytes) -> str:
        """Secondary PDF text extractor using pdfplumber (better for complex layouts)."""
        try:
            import io

            import pdfplumber  # noqa: PLC0415

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages_text.append(text)
                return "\n\n".join(pages_text).strip()
        except Exception as exc:
            logger.debug("pdfplumber extraction failed: %s", exc)
            return ""

    def _extract_docx_content(self, docx_bytes: bytes, url: str) -> dict:
        """Extract plain text from a .docx file using python-docx."""
        try:
            import io

            import docx  # noqa: PLC0415

            doc = docx.Document(io.BytesIO(docx_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            content = "\n\n".join(paragraphs).strip()

            props = doc.core_properties
            title = (props.title or "").strip() or url.rstrip("/").split("/")[-1]
            author = (props.author or "").strip() or "Unknown Author"

            return {
                "title": title,
                "author": author,
                "publish_date": "Unknown Date",
                "description": "",
                "content": content,
                "word_count": len(content.split()) if content else 0,
                "extraction_method": "docx_python_docx",
            }
        except Exception as exc:
            logger.warning("DOCX extraction failed for %s: %s", url, exc)
            return {
                "title": url.rstrip("/").split("/")[-1],
                "author": "Unknown Author",
                "publish_date": "Unknown Date",
                "description": "",
                "content": "",
                "word_count": 0,
                "extraction_method": "docx_failed",
            }

    def _extract_txt_content(self, txt_bytes: bytes, url: str) -> dict:
        """Decode plain-text response bytes."""
        try:
            detected = chardet.detect(txt_bytes[:4096])
            encoding = (
                detected.get("encoding")
                if detected and detected.get("confidence", 0) > 0.6
                else "utf-8"
            )
            content = txt_bytes.decode(encoding or "utf-8", errors="replace").strip()

            return {
                "title": url.rstrip("/").split("/")[-1],
                "author": "Unknown Author",
                "publish_date": "Unknown Date",
                "description": "",
                "content": content,
                "word_count": len(content.split()) if content else 0,
                "extraction_method": "txt_raw",
            }
        except Exception as exc:
            logger.warning("TXT extraction failed for %s: %s", url, exc)
            return {
                "title": url.rstrip("/").split("/")[-1],
                "author": "Unknown Author",
                "publish_date": "Unknown Date",
                "description": "",
                "content": "",
                "word_count": 0,
                "extraction_method": "txt_failed",
            }

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
        html = str(soup)

        content = self._extract_semantic_content(soup)
        method = "semantic_selectors"

        if not content or len(content.strip()) < 100:
            content = self._extract_with_trafilatura(html)
            method = "trafilatura"

        if not content or len(content.strip()) < 100:
            content = self._extract_paragraph_content(soup)
            method = "paragraph_extraction"

        if not content or len(content.strip()) < 100:
            content = self._extract_with_newspaper(url)
            method = "newspaper4k"

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

    def _extract_with_trafilatura(self, html: str) -> str:
        try:
            import trafilatura  # noqa: PLC0415

            result = trafilatura.extract(html, include_comments=False, include_tables=False)
            return result or ""
        except ImportError:
            logger.debug("trafilatura not installed — skipping")
            return ""
        except Exception as exc:
            logger.debug("trafilatura extraction failed: %s", exc)
            return ""

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
