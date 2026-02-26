"""
JS-Rendering Scraper — Legitimate Browser Automation
=====================================================

Uses Selenium to render JavaScript-heavy pages that cannot be scraped with
plain HTTP requests.

Design principles:
- Standard Chrome/Firefox driver — no anti-detection patches.
- No fingerprint spoofing, no stealth scripts, no Cloudflare bypass.
- Only used when standard HTTP extraction returns insufficient content.
- Respects robots.txt and site Terms of Service.

Requirements (optional, install if JS rendering is needed):
    pip install selenium webdriver-manager
"""

from __future__ import annotations

import logging
import time

from bs4 import BeautifulSoup

from config import config

logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore[import]

    _SELENIUM_AVAILABLE = True
except ImportError:
    _SELENIUM_AVAILABLE = False


class JsRenderingScraper:
    """Fetch page HTML after JavaScript execution using a headless browser.

    This is a last-resort fallback for pages that genuinely require JS
    to render their content (e.g. React/Vue SPAs). It does NOT attempt to
    bypass authentication, WAF, or any other access controls.
    """

    def __init__(self) -> None:
        if not _SELENIUM_AVAILABLE:
            raise ImportError(
                "selenium and webdriver-manager are required for JS rendering. "
                "Install with: pip install selenium webdriver-manager"
            )

    def fetch_rendered_html(self, url: str, wait_seconds: int = 5) -> str:
        """Return page HTML after JS rendering.

        Args:
            url: The public URL to render.
            wait_seconds: Seconds to wait for JS to settle after page load.

        Returns:
            Page HTML as a string.

        Raises:
            Exception on driver errors.
        """
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--user-agent=" + config.scraping.user_agents[0])

        import os
        chrome_bin = os.environ.get("CHROME_BIN")
        if not chrome_bin and os.environ.get("RENDER"):
            default_render_bin = "/opt/render/project/src/opt/chrome/chrome-linux64/chrome"
            if os.path.exists(default_render_bin):
                chrome_bin = default_render_bin
                
        if chrome_bin:
            options.binary_location = chrome_bin

        driver = None
        try:
            render_driver = "/opt/render/project/src/opt/chrome/chromedriver-linux64/chromedriver"
            if os.environ.get("RENDER") and os.path.exists(render_driver):
                # Ensure the driver is executable
                os.chmod(render_driver, 0o755)
                service = Service(render_driver)
            else:
                service = Service(ChromeDriverManager().install())
                
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(config.scraping.timeout)

            logger.info("JS rendering: fetching %s", url)
            driver.get(url)

            # Wait for readyState == "complete"
            WebDriverWait(driver, config.scraping.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(wait_seconds)  # Allow extra JS to finish

            return driver.page_source

        finally:
            if driver:
                driver.quit()

    def scrape_article(self, url: str) -> dict:
        """Render *url* and extract article content.

        Delegates content extraction to WebScraper helpers to stay DRY.
        """
        # Inline import to avoid circular dependency at module level
        from .web_scraper import WebScraper, _check_ssrf  # noqa: PLC0415

        # SSRF guard first — JS rendering must respect the same rules
        _check_ssrf(url)

        html = self.fetch_rendered_html(url)
        soup = BeautifulSoup(html, "html.parser")

        extractor = WebScraper()
        extractor._remove_unwanted_elements(soup)

        content = extractor._extract_semantic_content(soup)
        if not content or len(content.strip()) < 100:
            content = extractor._extract_paragraph_content(soup)
        if not content or len(content.strip()) < 50:
            content = soup.get_text(separator=" ", strip=True)

        return {
            "title": extractor._extract_title(soup),
            "author": extractor._extract_author(soup),
            "publish_date": extractor._extract_publish_date(soup),
            "description": extractor._extract_description(soup),
            "content": content.strip(),
            "word_count": len(content.split()) if content else 0,
            "extraction_method": "js_rendering",
            "url": url,
            "scraped_at": __import__("time").time(),
        }
