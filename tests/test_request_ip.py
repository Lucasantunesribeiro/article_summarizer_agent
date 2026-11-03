"""IP do cliente para rate limiting: X-Forwarded-For só via proxy confiável."""

from __future__ import annotations

import pytest
from flask import Flask

from presentation.blueprints.helpers import get_request_ip

app = Flask(__name__)


def _ip(headers=None, remote="203.0.113.9"):
    with app.test_request_context("/", headers=headers or {}, environ_base={"REMOTE_ADDR": remote}):
        return get_request_ip()


def test_ignores_forwarded_header_without_trusted_proxy(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    # Cliente forjando o header não muda a chave do rate limit.
    assert _ip({"X-Forwarded-For": "1.2.3.4"}) == "203.0.113.9"


def test_uses_value_appended_by_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    # "1.2.3.4" foi forjado pelo cliente; "198.51.100.7" foi anexado pelo proxy.
    assert _ip({"X-Forwarded-For": "1.2.3.4, 198.51.100.7"}) == "198.51.100.7"


@pytest.mark.parametrize("header", [None, ""])
def test_falls_back_to_remote_addr_when_header_missing(monkeypatch, header):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "2")
    headers = {} if header is None else {"X-Forwarded-For": header}
    assert _ip(headers) == "203.0.113.9"


def test_invalid_hops_value_is_ignored(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "abc")
    assert _ip({"X-Forwarded-For": "1.2.3.4"}) == "203.0.113.9"
