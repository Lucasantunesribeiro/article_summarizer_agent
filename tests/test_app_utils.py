"""Utility tests for API helpers and shared infrastructure."""

from __future__ import annotations

from pathlib import Path

from modules.file_manager import FileManager
from modules.rate_limiter import InMemoryRateLimiter
from modules.url_utils import canonicalize_url
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


class TestCanonicalizeUrl:
    def test_removes_tracking_params_and_fragment(self):
        url = (
            "https://www.estacio.br/blog/aluno/o-que-e-um-artigo-cientifico"
            "?srsltid=abc&utm_source=google&fbclid=xyz&page=2#section"
        )

        assert canonicalize_url(url) == (
            "https://www.estacio.br/blog/aluno/o-que-e-um-artigo-cientifico?page=2"
        )

    def test_preserves_functional_query_params(self):
        url = "https://example.com/search?q=python&lang=pt-BR"

        assert canonicalize_url(url) == "https://example.com/search?q=python&lang=pt-BR"


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


class TestFileManagerCacheKey:
    def test_tracking_variants_share_the_same_cache_key(self, monkeypatch, tmp_path):
        from config import config

        monkeypatch.setattr(config.output, "output_dir", str(tmp_path / "outputs"))
        monkeypatch.setattr(config.output, "cache_dir", str(tmp_path / ".cache"))

        file_manager = FileManager()
        canonical_url = "https://www.estacio.br/blog/aluno/o-que-e-um-artigo-cientifico"
        tracked_url = (
            canonical_url + "?srsltid=abc&utm_source=google&utm_campaign=spring&fbclid=xyz123"
        )

        assert file_manager._get_cache_key(canonical_url) == file_manager._get_cache_key(
            tracked_url
        )
