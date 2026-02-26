"""
Tests for SSRF protection in modules/web_scraper.py
"""

import pytest

from modules.web_scraper import _check_ssrf


class TestSSRFBlocking:
    """Private / internal addresses must be blocked."""

    def _assert_blocked(self, url: str) -> None:
        with pytest.raises(ValueError, match=r"Blocked|Invalid|Cannot|Rejected|unsupported"):
            _check_ssrf(url)

    # --- Scheme validation ---

    def test_ftp_scheme_rejected(self):
        self._assert_blocked("ftp://example.com/file")

    def test_file_scheme_rejected(self):
        self._assert_blocked("file:///etc/passwd")

    def test_javascript_scheme_rejected(self):
        self._assert_blocked("javascript:alert(1)")

    # --- Loopback ---

    def test_localhost_blocked(self):
        self._assert_blocked("http://localhost/")

    def test_127_0_0_1_blocked(self):
        self._assert_blocked("http://127.0.0.1/secret")

    def test_127_0_0_2_blocked(self):
        self._assert_blocked("http://127.0.0.2/")

    # --- RFC-1918 private ranges ---

    def test_10_network_blocked(self):
        self._assert_blocked("http://10.0.0.1/internal")

    def test_172_16_network_blocked(self):
        self._assert_blocked("http://172.16.0.1/")

    def test_192_168_network_blocked(self):
        self._assert_blocked("http://192.168.1.1/router")

    # --- Link-local / metadata ---

    def test_metadata_endpoint_blocked(self):
        # AWS/GCP/Azure metadata endpoint
        self._assert_blocked("http://169.254.169.254/latest/meta-data/")

    def test_link_local_blocked(self):
        self._assert_blocked("http://169.254.100.1/")

    # --- Special hostnames ---

    def test_dot_local_blocked(self):
        self._assert_blocked("http://myserver.local/api")

    def test_dot_internal_blocked(self):
        self._assert_blocked("http://service.internal/health")

    # --- Allowed (public internet) ---

    def test_public_https_allowed(self):
        # Should NOT raise — example.com is a public domain
        _check_ssrf("https://example.com/article")

    def test_public_http_allowed(self):
        _check_ssrf("http://example.com/")

    def test_public_with_path_and_query_allowed(self):
        _check_ssrf("https://news.ycombinator.com/item?id=12345")


class TestURLValidation:
    """URL format edge cases."""

    def test_no_scheme_raises(self):
        with pytest.raises(ValueError):
            _check_ssrf("example.com")

    def test_empty_raises(self):
        with pytest.raises((ValueError, Exception)):
            _check_ssrf("")
