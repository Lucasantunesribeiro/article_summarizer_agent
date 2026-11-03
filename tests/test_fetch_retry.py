"""Retry, redirects e SSRF do fetch de artigos (WebScraper._fetch) — sem rede."""

from __future__ import annotations

import itertools

import pytest
import requests

from modules.circuit_breaker import circuit_breaker
from modules.retry import RetryBudgetExceeded, RetryPolicy
from modules.web_scraper import WebScraper, _check_ssrf, classify_fetch_error

HTML = "<html><body><article>" + "<p>" + "texto " * 200 + "</p></article></body></html>"
_host_ids = itertools.count()


def unique_url(path="/artigo"):
    return f"https://site{next(_host_ids)}.example{path}"


class FakeResponse:
    def __init__(self, status=200, body=HTML, headers=None):
        self.status_code = status
        self.headers = {"Content-Type": "text/html; charset=utf-8", **(headers or {})}
        self._body = body.encode() if isinstance(body, str) else body
        self.encoding = "utf-8"
        self._content = None
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def iter_content(self, chunk_size=65536):
        yield self._body

    def close(self):
        self.closed = True


class ScriptedSession:
    """Session falsa: cada item do roteiro é uma resposta ou exceção."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, BaseException):
            raise item
        return item


class Sleeper:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


POLICY = RetryPolicy(max_attempts=4, base_delay=1, max_delay=8, total_timeout=120)


def make_scraper(script, policy=POLICY):
    sleeper = Sleeper()
    scraper = WebScraper(retry_policy=policy, sleep=sleeper)
    scraper.session = ScriptedSession(script)
    return scraper, sleeper


@pytest.fixture(autouse=True)
def _dns(public_dns):
    return public_dns


class TestFetchRetry:
    def test_retries_5xx_then_succeeds(self):
        scraper, sleeper = make_scraper([FakeResponse(503), FakeResponse(502), FakeResponse(200)])
        response = scraper._fetch(unique_url(), {})
        assert response.status_code == 200
        assert len(scraper.session.calls) == 3
        assert len(sleeper.calls) == 2
        assert all(0 <= s <= 8 for s in sleeper.calls)  # jitter dentro do teto

    def test_respects_retry_after_on_429(self):
        scraper, sleeper = make_scraper(
            [FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200)]
        )
        scraper._fetch(unique_url(), {})
        assert sleeper.calls == [7.0]

    def test_retries_timeouts_and_connection_errors(self):
        scraper, sleeper = make_scraper(
            [requests.Timeout("t"), requests.ConnectionError("c"), FakeResponse(200)]
        )
        assert scraper._fetch(unique_url(), {}).status_code == 200
        assert len(scraper.session.calls) == 3

    @pytest.mark.parametrize("status", [400, 401, 404, 410, 422])
    def test_client_errors_are_not_retried(self, status):
        url = unique_url()
        scraper, sleeper = make_scraper([FakeResponse(status)])
        with pytest.raises(requests.HTTPError):
            scraper._fetch(url, {})
        assert len(scraper.session.calls) == 1
        assert sleeper.calls == []
        # 4xx não conta como host indisponível
        host = url.split("/")[2]
        assert circuit_breaker.get_status(host)["failure_count"] == 0

    def test_ssl_error_is_not_retried(self):
        scraper, _ = make_scraper([requests.exceptions.SSLError("cert")])
        with pytest.raises(requests.exceptions.SSLError):
            scraper._fetch(unique_url(), {})
        assert len(scraper.session.calls) == 1

    def test_gives_up_after_max_attempts_and_records_circuit_failure(self):
        url = unique_url()
        scraper, sleeper = make_scraper([FakeResponse(503)])
        with pytest.raises(requests.HTTPError):
            scraper._fetch(url, {})
        assert len(scraper.session.calls) == POLICY.max_attempts
        host = url.split("/")[2]
        assert circuit_breaker.get_status(host)["failure_count"] == 1

    def test_total_timeout_budget(self):
        policy = RetryPolicy(max_attempts=10, base_delay=1, max_delay=8, total_timeout=5)
        scraper, _ = make_scraper([FakeResponse(503, headers={"Retry-After": "30"})], policy)
        with pytest.raises(RetryBudgetExceeded):
            scraper._fetch(unique_url(), {})
        assert len(scraper.session.calls) == 1

    def test_per_request_timeout_never_exceeds_config(self, monkeypatch):
        from config import config

        # Fixa o valor: outros testes alteram config.scraping.timeout via settings.
        monkeypatch.setattr(config.scraping, "timeout", 30)
        scraper, _ = make_scraper([FakeResponse(200)])
        scraper._fetch(unique_url(), {})
        _, kwargs = scraper.session.calls[0]
        assert 1 <= kwargs["timeout"] <= 30
        assert kwargs["allow_redirects"] is False
        assert kwargs["verify"] is True

    def test_body_size_limit_is_not_retried(self, monkeypatch):
        from config import config

        monkeypatch.setattr(config.scraping, "max_content_bytes", 100)
        scraper, _ = make_scraper([FakeResponse(200, body="x" * 1000)])
        with pytest.raises(ValueError, match="exceeded"):
            scraper._fetch(unique_url(), {})
        assert len(scraper.session.calls) == 1

    def test_classify_fetch_error(self):
        assert classify_fetch_error(requests.Timeout()).retryable
        assert classify_fetch_error(requests.HTTPError(response=FakeResponse(504))).retryable
        assert not classify_fetch_error(requests.HTTPError(response=FakeResponse(403))).retryable
        assert not classify_fetch_error(ValueError("Blocked")).retryable


class TestRedirectSSRF:
    def test_follows_public_redirect(self):
        scraper, _ = make_scraper(
            [
                FakeResponse(301, headers={"Location": "https://outro.example/final"}),
                FakeResponse(200),
            ]
        )
        response = scraper._fetch(unique_url(), {})
        assert response.status_code == 200
        assert scraper.session.calls[1][0] == "https://outro.example/final"

    @pytest.mark.parametrize(
        "location",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:8080/admin",
            "http://[::ffff:127.0.0.1]/",
            "http://10.0.0.5/",
            "http://metadata.internal/",
            "file:///etc/passwd",
        ],
    )
    def test_redirect_to_internal_address_is_blocked(self, location):
        scraper, _ = make_scraper(
            [FakeResponse(302, headers={"Location": location}), FakeResponse(200)]
        )
        with pytest.raises(ValueError, match=r"Blocked|Rejected"):
            scraper._fetch(unique_url(), {})
        # Só o primeiro salto (público) foi requisitado; o interno nunca.
        assert len(scraper.session.calls) == 1

    def test_too_many_redirects(self):
        scraper, _ = make_scraper(
            [FakeResponse(302, headers={"Location": "https://loop.example/a"})]
        )
        with pytest.raises(ValueError, match="redirects"):
            scraper._fetch(unique_url(), {})


class TestSSRFAddressRanges:
    @pytest.mark.parametrize(
        "url",
        [
            "http://0.0.0.0/",
            "http://[::]/",
            "http://[::1]/",
            "http://[::ffff:169.254.169.254]/",
            "http://[fd00:ec2::254]/",
            "http://224.0.0.1/",
            "http://100.100.100.200/",  # metadata Alibaba (CGNAT)
            "http://[64:ff9b::a9fe:a9fe]/",  # NAT64 de 169.254.169.254
        ],
    )
    def test_blocked(self, url):
        with pytest.raises(ValueError, match="Blocked"):
            _check_ssrf(url)

    def test_hostname_resolving_to_metadata_is_blocked(self, monkeypatch):
        import socket

        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))],
        )
        with pytest.raises(ValueError, match="Blocked"):
            _check_ssrf("http://inocente.example/")

    def test_public_ip_allowed(self):
        _check_ssrf("https://93.184.216.34/")
