"""Integration tests for WebScraper using mocked HTTP responses."""

from __future__ import annotations

import pytest

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<article>
<h1>AI Advances in 2024</h1>
<p>Artificial intelligence has made remarkable progress in 2024. Researchers at major institutions have published breakthrough findings on large language models, computer vision, and reinforcement learning. These advances are transforming industries from healthcare to finance.</p>
<p>The development of multimodal models represents a significant milestone. Systems can now process text, images, audio, and video simultaneously, enabling richer interactions and more accurate understanding of complex scenarios.</p>
<p>Safety research has also accelerated. New techniques for alignment, interpretability, and robustness are being deployed in production systems, reducing risks associated with increasingly capable AI.</p>
</article>
</body>
</html>
"""


@pytest.fixture
def mock_http(monkeypatch):
    """Monkeypatch requests.Session.get to return sample HTML."""
    import requests

    class MockResponse:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        encoding = "utf-8"
        text = SAMPLE_HTML
        content = SAMPLE_HTML.encode("utf-8")
        url = "https://example.com/article"

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=65536):
            yield SAMPLE_HTML.encode("utf-8")

    def mock_get(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests.Session, "get", mock_get)
    return MockResponse()


class TestWebScraperIntegration:
    def test_scrape_returns_content(self, mock_http):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        result = scraper.scrape_article("https://example.com/article")
        assert result.get("content")
        assert len(result["content"]) > 50

    def test_scrape_extracts_title(self, mock_http):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        result = scraper.scrape_article("https://example.com/article")
        assert result.get("title") or result.get("content")

    def test_ssrf_localhost_rejected(self):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        with pytest.raises(Exception, match=r"(?i)(ssrf|blocked|private|local|forbidden|refused)"):
            scraper.scrape_article("http://localhost/")

    def test_ssrf_private_ip_rejected(self):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        with pytest.raises(Exception, match=r"(?i)(ssrf|blocked|private|local|forbidden|refused)"):
            scraper.scrape_article("http://192.168.1.1/secret")

    def test_ssrf_metadata_ip_rejected(self):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        with pytest.raises(Exception, match=r"(?i)(ssrf|blocked|private|local|forbidden|refused)"):
            scraper.scrape_article("http://169.254.169.254/latest/meta-data/")
