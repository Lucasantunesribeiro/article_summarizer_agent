"""JWT authentication endpoints."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_ADMIN_USER = os.getenv("ADMIN_USER", "admin")
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not _ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Auth not configured (set ADMIN_PASSWORD)."}), 503

    if username != _ADMIN_USER or password != _ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Invalid credentials."}), 401

    access_token = create_access_token(
        identity=username, additional_claims={"role": "admin"}
    )
    refresh_token = create_refresh_token(identity=username)

    resp = jsonify(
        {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )
    # Also set HttpOnly cookies so the /historico HTML page can authenticate
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"success": True, "message": "Logged out."})
    unset_jwt_cookies(resp)
    return resp


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, additional_claims={"role": "admin"})
    resp = jsonify({"success": True, "access_token": access_token})
    set_access_cookies(resp, access_token)
    return resp
