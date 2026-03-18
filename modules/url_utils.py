"""Utilities for normalising externally supplied URLs."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_QUERY_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "gbraid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "mkt_tok",
        "srsltid",
        "wbraid",
    }
)
_TRACKING_QUERY_PREFIXES = ("utm_",)


def canonicalize_url(url: str) -> str:
    """Return a canonical URL for internal fetch, cache, and fallback operations."""
    candidate = (url or "").strip()
    if not candidate:
        return ""

    parsed = urlsplit(candidate)
    if not parsed.scheme or not parsed.netloc:
        return candidate

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_QUERY_PARAMS
        and not key.lower().startswith(_TRACKING_QUERY_PREFIXES)
    ]

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )
