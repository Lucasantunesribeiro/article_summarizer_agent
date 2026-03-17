"""Shared helpers for presentation layer."""

from __future__ import annotations

import pathlib
from typing import Any

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from config import config


def get_container():
    return current_app.extensions["container"]


def get_request_ip() -> str:
    return (
        request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
        .split(",")[0]
        .strip()
    )


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
