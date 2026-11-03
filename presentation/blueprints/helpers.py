"""Shared helpers for presentation layer."""

from __future__ import annotations

import os
import pathlib
from typing import Any

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from config import config


def get_container():
    return current_app.extensions["container"]


def get_request_ip() -> str:
    """IP do cliente usado no rate limiting e na auditoria.

    O primeiro valor de ``X-Forwarded-For`` é escrito pelo próprio cliente;
    usá-lo permitia furar o rate limit trocando o header a cada requisição.
    Só confia no header quando ``TRUSTED_PROXY_HOPS`` > 0 e, nesse caso, pega
    o valor anexado pelo proxy confiável mais externo (N-ésimo da direita).
    """
    remote = request.remote_addr or "unknown"
    try:
        hops = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))
    except ValueError:
        hops = 0
    if hops <= 0:
        return remote
    forwarded = [part.strip() for part in request.headers.get("X-Forwarded-For", "").split(",")]
    forwarded = [part for part in forwarded if part]
    if len(forwarded) < hops:
        return remote
    return forwarded[-hops]


def enforce_rate_limit(profile: str):
    limiter = get_container().rate_limiters[profile]
    if limiter.is_allowed(get_request_ip()):
        return None
    return jsonify({"success": False, "error": "Rate limit exceeded."}), 429


def get_authenticated_user():
    container = get_container()
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if not identity:
            return None
        return container.user_repository.get_by_id(str(identity))
    except Exception:
        return None


def is_admin_request() -> bool:
    user = get_authenticated_user()
    return bool(user and user.can_manage_system())


def get_claims() -> dict[str, Any]:
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt()
    except Exception:
        return {}


def validate_download_path(path: str) -> pathlib.Path | None:
    allowed_dir = pathlib.Path(config.output.output_dir).resolve()
    resolved_path = pathlib.Path(path).resolve()
    if not resolved_path.is_relative_to(allowed_dir):
        return None
    return resolved_path
