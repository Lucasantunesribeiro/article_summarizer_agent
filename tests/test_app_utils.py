"""Utility tests for API helpers and shared infrastructure."""

from __future__ import annotations

from pathlib import Path

from modules.rate_limiter import InMemoryRateLimiter
from presentation.blueprints.api import _normalise_url
from presentation.blueprints.helpers import validate_download_path


class TestNormaliseUrl:
    def test_adds_https_to_bare_domain(self):
        assert _normalise_url("example.com") == "https://example.com"

    def test_strips_www_from_bare_input(self):
        assert _normalise_url("www.example.com") == "https://example.com"

    def test_preserves_existing_scheme(self):
        assert _normalise_url("https://www.example.com") == "https://www.example.com"

    def test_trims_whitespace(self):
        assert _normalise_url("  example.com/path  ") == "https://example.com/path"


class TestRateLimit:
    def test_first_request_allowed(self):
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("10.0.0.1") is True

    def test_exceeds_limit_returns_false(self):
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        ip = "10.0.0.2"
        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is False


class TestValidateDownloadPath:
    def test_rejects_path_outside_output_dir(self, monkeypatch, tmp_path):
        from config import config

        monkeypatch.setattr(config.output, "output_dir", str(tmp_path / "outputs"))
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")

        assert validate_download_path(str(outside)) is None

    def test_accepts_path_inside_output_dir(self, monkeypatch, tmp_path):
        from config import config

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        monkeypatch.setattr(config.output, "output_dir", str(output_dir))
        file_path = output_dir / "summary.txt"
        file_path.write_text("ok", encoding="utf-8")

        resolved = validate_download_path(str(file_path))
        assert resolved == Path(file_path).resolve()
